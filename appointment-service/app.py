from flask import Flask, request, jsonify
import uuid
from datetime import datetime
import threading
import time
import psutil
import os
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

app = Flask(__name__)

# Global dictionary to store appointments - THIS CREATES A MEMORY LEAK
appointments_storage = {}

# Initialize OpenTelemetry metrics
metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(),
    export_interval_millis=30000  # Export every 60 seconds
)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
meter = metrics.get_meter(__name__)

# Create memory usage histogram
memory_usage_histogram = meter.create_histogram(
    name="MemoryUsage",
    description="Memory usage of the appointment service in MB",
    unit="Megabytes"
)

def emit_memory_metrics():
    """Periodically emit memory usage metrics"""
    while True:
        try:
            # Calculate process memory usage in MB
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            memory_usage_histogram.record(memory_mb, {"ServiceName": "AppointmentService"})
            print(f"Memory usage emitted: {memory_mb} MB (appointments count: {len(appointments_storage)})")
            time.sleep(10)  # Emit every 10 seconds
        except Exception as e:
            print(f"Error emitting memory metrics: {e}")
            time.sleep(10)

# Start metrics emission thread
metrics_thread = threading.Thread(target=emit_memory_metrics, daemon=True)
metrics_thread.start()

@app.route('/createAppointment', methods=['POST'])
def create_appointment():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Generate unique appointment ID
        appointment_id = str(uuid.uuid4())
        
        # Create appointment object
        appointment = {
            'id': appointment_id,
            'patient_name': data.get('patient_name', ''),
            'doctor_name': data.get('doctor_name', ''),
            'appointment_date': data.get('appointment_date', ''),
            'appointment_time': data.get('appointment_time', ''),
            'notes': data.get('notes', ''),
            'created_at': datetime.now().isoformat()
        }
        
        # Store in global dictionary - MEMORY LEAK: Never removed
        appointments_storage[appointment_id] = appointment
        # print(f"Total appointments: {len(appointments_storage)}")
        # print(f"appointments_storage bytes: {len(str(appointments_storage).encode('utf-8'))}")
        return jsonify({
            'success': True,
            'appointment_id': appointment_id,
            'message': 'Appointment created successfully',
            'total_appointments': len(appointments_storage)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
    