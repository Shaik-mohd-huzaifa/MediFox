#!/usr/bin/env python3
"""
Script to create multiple dummy patients for MediFox demo purposes.
This script creates local patient files with fake Eka Care IDs for simulating integration.
"""

import os
import json
import random
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Sample data for generating realistic but fake patient information
FIRST_NAMES = [
    "Raj", "Priya", "Amit", "Neha", "Vikram", "Anjali", "Sanjay", "Pooja",
    "Arjun", "Meera", "Rahul", "Sunita", "Karthik", "Ananya", "Rajesh", "Lakshmi"
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Reddy", "Verma", "Joshi", "Kumar", "Gupta",
    "Malhotra", "Shah", "Desai", "Chatterjee", "Nair", "Mehta", "Agarwal", "Iyer"
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

ALLERGIES = [
    "None", "Penicillin", "Aspirin", "Dairy", "Peanuts", "Shellfish",
    "Soy", "Tree nuts", "Wheat", "Eggs", "Latex"
]

HEALTH_CONDITIONS = [
    "None", "Asthma", "Diabetes", "Hypertension", "Arthritis",
    "Thyroid disorder", "Migraine", "Anemia", "GERD", "Seasonal allergies"
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune",
    "Kolkata", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur"
]

STATES = [
    "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Telangana",
    "West Bengal", "Gujarat", "Rajasthan", "Uttar Pradesh"
]

DOCTORS = [
    {"id": "DOC123", "name": "Dr. Ravi Sharma", "specialty": "General Physician"},
    {"id": "DOC456", "name": "Dr. Sunita Patel", "specialty": "Cardiologist"},
    {"id": "DOC789", "name": "Dr. Vikram Mehta", "specialty": "Dermatologist"},
    {"id": "DOC234", "name": "Dr. Anjali Gupta", "specialty": "Pediatrician"},
    {"id": "DOC567", "name": "Dr. Prakash Iyer", "specialty": "Orthopedic"}
]


def generate_phone():
    """Generate a valid-looking Indian phone number"""
    prefix = random.choice(["9", "8", "7", "6"])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return prefix + rest


def generate_random_date(start_year=1950, end_year=2000):
    """Generate a random date of birth"""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Simplified to avoid month-specific logic
    return date(year, month, day)


def calculate_age(birth_date):
    """Calculate age based on birth date"""
    today = date.today()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


def generate_patient_data():
    """Generate a random patient profile with realistic but fake data"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = random.choice(["male", "female"])
    
    dob = generate_random_date()
    dob_str = dob.strftime("%Y-%m-%d")
    
    blood_group = random.choice(BLOOD_GROUPS)
    allergies = random.choice(ALLERGIES)
    condition = random.choice(HEALTH_CONDITIONS)
    
    city = random.choice(CITIES)
    state = random.choice(STATES)
    
    phone_number = generate_phone()
    
    # Generate a unique consistent ID based on phone number for demo
    patient_id = f"P{phone_number[-5:]}"
    
    # Generate fake Eka Care ID
    eka_care_id = f"EKA{random.randint(100000, 999999)}"
    
    # Create the patient record in our internal format
    patient = {
        "id": patient_id,
        "eka_care_id": eka_care_id,  # Fake Eka Care ID to simulate integration
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "gender": gender,
        "date_of_birth": dob_str,
        "age": calculate_age(dob),
        "blood_group": blood_group,
        "allergies": allergies,
        "health_conditions": condition,
        "phone_number": phone_number,
        "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "address": {
            "street": f"{random.randint(1, 100)} Example Street",
            "city": city,
            "state": state,
            "postal_code": f"{random.randint(100000, 999999)}"
        },
        "emergency_contact": {
            "name": f"{random.choice(FIRST_NAMES)} {last_name}",
            "relationship": random.choice(["Spouse", "Parent", "Sibling", "Child"]),
            "phone": generate_phone()
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    return patient, patient_id, phone_number, eka_care_id


def create_patient_locally(patient_data, patient_id):
    """Create the patient in local storage"""
    try:
        # Create data directory if it doesn't exist
        data_dir = Path(__file__).parent.parent / "data" / "patients"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Save patient data to file
        patient_file = data_dir / f"{patient_id}.json"
        with open(patient_file, 'w') as f:
            json.dump(patient_data, f, indent=2)
            
        print(f"Successfully created local patient record at {patient_file}")
        return True
        
    except Exception as e:
        print(f"Error creating local patient record: {e}")
        return False


def create_appointments_for_patient(patient_id, num_appointments=1):
    """Create some sample appointments for this patient"""
    try:
        appt_dir = Path(__file__).parent.parent / "data" / "appointments"
        appt_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now()
        appointments = []
        
        # Create past, present and future appointments
        for i in range(num_appointments):
            doctor = random.choice(DOCTORS)
            
            # Random appointment date within 30 days before or after today
            days_offset = random.randint(-30, 30)
            appt_date = today + timedelta(days=days_offset)
            
            # Random hour between 9 AM and 5 PM
            hour = random.randint(9, 17)
            minute = random.choice([0, 15, 30, 45])
            appt_date = appt_date.replace(hour=hour, minute=minute)
            
            # Determine status based on date
            if days_offset < 0:
                status = random.choice(["completed", "cancelled", "no-show"])
            elif days_offset == 0:
                status = "confirmed"
            else:
                status = "scheduled"
                
            appointment = {
                "id": f"APPT{random.randint(10000, 99999)}",
                "eka_id": f"EKA-APPT-{random.randint(10000, 99999)}",
                "doctor_id": doctor["id"],
                "doctor_name": doctor["name"],
                "specialty": doctor["specialty"],
                "datetime": appt_date.isoformat(),
                "status": status,
                "reason": random.choice(["Regular checkup", "Follow-up", "Consultation", "Vaccination", "Emergency"]),
                "notes": "This is a sample appointment for demo purposes.",
                "created_at": (appt_date - timedelta(days=random.randint(1, 10))).isoformat(),
                "updated_at": today.isoformat()
            }
            
            appointments.append(appointment)
        
        # Create appointment data structure
        appointment_data = {
            "patient_id": patient_id,
            "updated_at": datetime.now().isoformat(),
            "appointments": appointments
        }
        
        # Save to file
        appt_file = appt_dir / f"{patient_id}.json"
        with open(appt_file, 'w') as f:
            json.dump(appointment_data, f, indent=2)
            
        print(f"Successfully created {num_appointments} appointments for patient at {appt_file}")
        return appointments
    
    except Exception as e:
        print(f"Error creating appointments: {e}")
        return []


def main():
    """Main function to create multiple dummy patients"""
    print("Creating dummy patients for MediFox demo...")
    
    # Use default value for number of patients
    num_patients = 3  # Default to creating 3 patients

    print(f"\nCreating {num_patients} dummy patient(s) with Eka Care integration simulation...\n")
    
    # Keep track of all created patients
    created_patients = []
    
    for i in range(num_patients):
        print(f"\n--- Creating Patient {i+1}/{num_patients} ---")
        
        # Generate random patient data
        patient_data, patient_id, phone_number, eka_care_id = generate_patient_data()
        
        # Create patient in local storage
        local_success = create_patient_locally(patient_data, patient_id)
        
        if local_success:
            # Create 1-3 appointments for this patient
            num_appointments = random.randint(1, 3)
            appointments = create_appointments_for_patient(patient_id, num_appointments)
            
            # Add to tracking list
            created_patients.append({
                "local_id": patient_id,
                "eka_id": eka_care_id,
                "name": patient_data['full_name'],
                "phone": phone_number,
                "appointments": len(appointments)
            })
    
    # Print summary of all created patients
    print("\n" + "="*60)
    print(f"{len(created_patients)} DUMMY PATIENT(S) CREATED SUCCESSFULLY WITH EKA CARE IDs")
    print("="*60)
    
    for i, patient in enumerate(created_patients):
        print(f"Patient #{i+1}:")
        print(f"  Name: {patient['name']}")
        print(f"  Local ID: {patient['local_id']}")
        print(f"  Eka Care ID: {patient['eka_id']}")
        print(f"  Phone Number: {patient['phone']}")
        print(f"  Appointments: {patient['appointments']}")
        print()
    
    print("="*60)
    print("\nYou can now use these patients in your MediFox demos.")
    print("The patients have fake Eka Care IDs to simulate integration.")
    print("Use either the Patient ID or Phone Number to identify these patients.")
    
    # Create a reference file with all dummy patients
    try:
        reference_file = Path(__file__).parent / "dummy_patients_reference.json"
        with open(reference_file, 'w') as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "patients": created_patients
            }, f, indent=2)
        print(f"\nA reference file has been created at: {reference_file}")
    except Exception as e:
        print(f"\nFailed to create reference file: {e}")
    

if __name__ == "__main__":
    main()
