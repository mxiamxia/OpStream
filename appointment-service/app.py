from flask import Flask, request, jsonify
import uuid
from datetime import datetime, timedelta
import threading
import time
import psutil
import os
import heapq
from collections import OrderedDict
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

app = Flask(__name__)

# Use OrderedDict to efficiently manage appointments with LRU behavior
# This will help prevent memory leaks by limiting storage size
MAX_APPOINTMENTS = 1000  # Maximum number of appointments to store
appointments_storage = OrderedDict()

# Initialize OpenTelemetry metrics
metric_reader = PeriodicExportingMetricReader(
    ConsoleMetricExporter(),
    export_interval_millis=30000  # Export every 30 seconds
)
metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
meter = metrics.get_meter(__name__)

# Create memory usage histogram
memory_usage_histogram = meter.create_histogram(
    name="MemoryUsage",
    description="Memory usage of the appointment service in MB",
    unit="Megabytes"
)

# Create appointment count gauge
appointment_count_gauge = meter.create_gauge(
    name="AppointmentCount",
    description="Number of appointments in storage",
    unit="Count"
)

def cleanup_old_appointments():
    """Remove old appointments to prevent memory leaks"""
    try:
        # Keep only the most recent MAX_APPOINTMENTS
        while len(appointments_storage) > MAX_APPOINTMENTS:
            # Remove the oldest item (first inserted)
            appointments_storage.popitem(last=False)
            
        # Alternative: Remove appointments older than 30 days
        cutoff_date = datetime.now() - timedelta(days=30)
        keys_to_remove = []
        
        for appointment_id, appointment in list(appointments_storage.items()):
            created_at = datetime.fromisoformat(appointment['created_at'])
            if created_at < cutoff_date:
                keys_to_remove.append(appointment_id)
                
        for key in keys_to_remove:
            del appointments_storage[key]
            
    except Exception as e:
        print(f"Error during appointment cleanup: {e}")

def emit_memory_metrics():
    """Periodically emit memory usage metrics and clean up old appointments"""
    while True:
        try:
            # Calculate process memory usage in MB
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Record metrics
            memory_usage_histogram.record(memory_mb, {"ServiceName": "AppointmentService"})
            appointment_count_gauge.set(len(appointments_storage), {"ServiceName": "AppointmentService"})
            
            # Perform cleanup to manage memory
            cleanup_old_appointments()
            
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
        
        # Store in OrderedDict - will be managed by cleanup function
        appointments_storage[appointment_id] = appointment
        
        # If we're at capacity, trigger cleanup immediately
        if len(appointments_storage) > MAX_APPOINTMENTS:
            cleanup_old_appointments()
            
        return jsonify({
            'success': True,
            'appointment_id': appointment_id,
            'message': 'Appointment created successfully',
            'total_appointments': len(appointments_storage)
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add a route to get appointment details
@app.route('/appointment/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    appointment = appointments_storage.get(appointment_id)
    if appointment:
        # Move to end of OrderedDict to mark as recently used
        appointments_storage.move_to_end(appointment_id)
        return jsonify(appointment), 200
    return jsonify({'error': 'Appointment not found'}), 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
    