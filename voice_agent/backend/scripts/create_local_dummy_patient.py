#!/usr/bin/env python3
"""
Script to create a dummy patient for MediFox demo purposes.
This creates a patient in the local storage only.
"""

import os
import json
import random
from datetime import datetime, date
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
    
    # Create the patient record in our internal format
    patient = {
        "id": patient_id,
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
    
    # Add a fake Eka Care ID for simulating integration
    patient["eka_care_id"] = f"EKA{random.randint(100000, 999999)}"
    
    return patient, patient_id, phone_number


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


def main():
    """Main function to create a dummy patient"""
    print("Creating dummy patient for MediFox demo...")
    
    # Generate random patient data
    patient_data, patient_id, phone_number = generate_patient_data()
    
    # Create patient in local storage
    local_success = create_patient_locally(patient_data, patient_id)
    
    if local_success:
        # Also create a dummy appointments file for this patient
        try:
            appt_dir = Path(__file__).parent.parent / "data" / "appointments"
            appt_dir.mkdir(parents=True, exist_ok=True)
            
            # Example appointment data
            appointment_data = {
                "patient_id": patient_id,
                "updated_at": datetime.now().isoformat(),
                "appointments": [
                    {
                        "id": f"APPT{random.randint(10000, 99999)}",
                        "eka_id": f"EKA-APPT-{random.randint(10000, 99999)}",
                        "doctor_id": f"DOC{random.randint(100, 999)}",
                        "doctor_name": "Dr. Patel",
                        "specialty": "General Physician",
                        "datetime": (datetime.now().replace(hour=10, minute=30)).isoformat(),
                        "status": "confirmed",
                        "reason": "Regular checkup",
                        "notes": "Patient has reported mild fever for 2 days",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ]
            }
            
            appt_file = appt_dir / f"{patient_id}.json"
            with open(appt_file, 'w') as f:
                json.dump(appointment_data, f, indent=2)
                
            print(f"Successfully created appointments for patient at {appt_file}")
        except Exception as e:
            print(f"Error creating appointments: {e}")
    
    # Print summary
    print("\n" + "="*50)
    print("DUMMY PATIENT CREATED SUCCESSFULLY")
    print("="*50)
    print(f"Patient Name: {patient_data['full_name']}")
    print(f"Patient ID: {patient_id}")
    print(f"Phone Number: {phone_number}")
    print(f"Fake Eka Care ID: {patient_data['eka_care_id']}")
    print(f"Gender: {patient_data['gender']}")
    print(f"Date of Birth: {patient_data['date_of_birth']}")
    print(f"Age: {patient_data['age']}")
    print("="*50)
    print("\nYou can now use this patient in your MediFox demos.")
    print("Use either the Patient ID or Phone Number to identify this patient.")
    

if __name__ == "__main__":
    main()
