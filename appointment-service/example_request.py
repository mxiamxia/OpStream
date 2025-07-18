import requests
import json

# Example 1: Create a single appointment
def create_appointment_example():
    url = "http://localhost:5000/createAppointment"
    
    appointment_data = {
        "patient_name": "John Doe",
        "doctor_name": "Dr. Smith",
        "appointment_date": "2024-01-15",
        "appointment_time": "10:30 AM",
        "notes": "Regular checkup"
    }
    
    response = requests.post(url, json=appointment_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

# Example 2: Create multiple appointments to demonstrate memory leak
def demonstrate_memory_leak():
    base_url = "http://localhost:5000"
    
    # Create 100 appointments to show memory growth
    for i in range(100):
        appointment_data = {
            "patient_name": f"Patient {i+1}",
            "doctor_name": f"Dr. Doctor{i%10}",
            "appointment_date": "2024-01-15",
            "appointment_time": f"{9 + (i%8)}:00 AM",
            "notes": f"Appointment #{i+1}"
        }
        
        response = requests.post(f"{base_url}/createAppointment", json=appointment_data)
        
        if i % 10 == 0:  # Check memory every 10 appointments
            memory_response = requests.get(f"{base_url}/memory-stats")
            memory_data = memory_response.json()
            print(f"After {i+1} appointments: {memory_data['memory_usage_mb']:.2f} MB")

if __name__ == "__main__":
    print("Creating single appointment:")
    create_appointment_example()
    
    print("\nDemonstrating memory leak:")
    demonstrate_memory_leak()