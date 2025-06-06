#!/usr/bin/env python3
"""
Script to create a dummy patient for MediFox demo purposes.
This will create a patient both in the local storage and attempt to register with Eka Care.
"""

import os
import sys
import json
import asyncio
from datetime import datetime, date
import random
from pathlib import Path

# Add parent directory to path so we can import from our modules
sys.path.append(str(Path(__file__).parent.parent))

from integrations.eka_care_client import EkaCareClient, EkaCredentials
from dotenv import load_dotenv


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
    
    # Create the same patient in Eka Care format
    eka_patient = {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender.upper(),  # Assuming Eka Care uses uppercase
        "date_of_birth": dob_str,
        "blood_group": blood_group,
        "allergies": [allergies] if allergies != "None" else [],
        "medical_conditions": [condition] if condition != "None" else [],
        "phone_number": phone_number,
        "email": patient["email"],
        "address": {
            "line1": patient["address"]["street"],
            "city": city,
            "state": state,
            "pincode": patient["address"]["postal_code"]
        },
        "emergency_contacts": [{
            "name": patient["emergency_contact"]["name"],
            "relation": patient["emergency_contact"]["relationship"],
            "phone_number": patient["emergency_contact"]["phone"]
        }]
    }
    
    return patient, eka_patient, patient_id, phone_number


async def create_patient_in_eka_care(eka_patient_data, num_attempts=1):
    """Try to create the patient in Eka Care"""
    try:
        # Get credentials from environment variables
        client_id = os.environ.get("EKA_CLIENT_ID")
        client_secret = os.environ.get("EKA_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            print("Error: EKA_CLIENT_ID or EKA_CLIENT_SECRET not set in environment")
            return None
            
        # Initialize the Eka Care client with only client credentials
        credentials = EkaCredentials(
            client_id=client_id,
            client_secret=client_secret
            # No username or password needed
        )
        eka_client = EkaCareClient(credentials)
        
        # Login to Eka Care using client credentials flow
        login_success = await eka_client.login()
        if not login_success:
            print("Failed to log in to Eka Care. Check your client credentials.")
            return None
            
        print("Successfully logged in to Eka Care")
        
        # Create multiple patients if requested
        created_patients = []
        
        for i in range(num_attempts):
            # Add the patient
            response = await eka_client.add_patient(eka_patient_data)
            
            if response and "data" in response:
                patient_id = response['data'].get('id', 'unknown')
                print(f"Successfully created patient {i+1}/{num_attempts} in Eka Care with ID: {patient_id}")
                created_patients.append({
                    "id": patient_id,
                    "data": response['data']
                })
            else:
                print(f"Failed to create patient {i+1}/{num_attempts} in Eka Care: {response}")
        
        return created_patients if created_patients else None
    
    except Exception as e:
        print(f"Error creating patient in Eka Care: {e}")
        return None


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


async def main():
    """Main function to create a dummy patient"""
    print("Creating dummy patient(s) for MediFox demo...")
    
    # Load environment variables
    load_dotenv()
    
    # Check for Eka Care client credentials
    if not all([os.getenv(var) for var in ["EKA_CLIENT_ID", "EKA_CLIENT_SECRET"]]):
        print("Error: Eka Care client credentials not found in environment. Cannot create patients.")
        return
    
    # Ask how many dummy patients to create
    try:
        num_patients = int(input("How many dummy patients would you like to create? (1-5): "))
        num_patients = max(1, min(5, num_patients))  # Limit to 1-5 patients
    except ValueError:
        num_patients = 1
        print("Invalid input. Creating 1 patient.")

    print(f"\nCreating {num_patients} dummy patient(s)...\n")
    
    # Keep track of all created patients
    created_patients = []
    
    for i in range(num_patients):
        print(f"\n--- Creating Patient {i+1}/{num_patients} ---")
        
        # Generate random patient data
        patient_data, eka_patient_data, patient_id, phone_number = generate_patient_data()
        
        # Create patient in local storage
        local_success = create_patient_locally(patient_data, patient_id)
        
        # Try to create in Eka Care
        eka_patient_results = await create_patient_in_eka_care(eka_patient_data)
        
        # If successful, update the local record with the Eka Care ID
        if eka_patient_results and local_success:
            eka_patient_id = eka_patient_results[0]["id"]
            patient_data["eka_care_id"] = eka_patient_id
            create_patient_locally(patient_data, patient_id)
            
            # Add to tracking list
            created_patients.append({
                "local_id": patient_id,
                "eka_id": eka_patient_id,
                "name": patient_data['full_name'],
                "phone": phone_number
            })
    
    # Print summary of all created patients
    print("\n" + "="*50)
    print(f"{len(created_patients)} DUMMY PATIENT(S) CREATED SUCCESSFULLY")
    print("="*50)
    
    for i, patient in enumerate(created_patients):
        print(f"Patient #{i+1}:")
        print(f"  Name: {patient['name']}")
        print(f"  Local ID: {patient['local_id']}")
        print(f"  Eka Care ID: {patient['eka_id']}")
        print(f"  Phone Number: {patient['phone']}")
        print()
    
    print("="*50)
    print("\nYou can now use these patients in your MediFox demos.")
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
    asyncio.run(main())
