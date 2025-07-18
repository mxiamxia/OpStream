#!/bin/bash

# Create multiple appointments to demonstrate memory leak
echo -e "\n\nCreating multiple appointments to demonstrate memory leak..."
for i in {1..200}; do
  curl -s -X POST http://localhost:5000/createAppointment \
    -H "Content-Type: application/json" \
    -d "{
      \"patient_name\": \"Patient $i\",
      \"doctor_name\": \"Dr. Test\",
      \"appointment_date\": \"2024-01-25\",
      \"appointment_time\": \"$((9 + i % 8)):00 AM\",
      \"notes\": \"Test appointment $i\"
    }" > /dev/null
  
  sleep 0.1
done