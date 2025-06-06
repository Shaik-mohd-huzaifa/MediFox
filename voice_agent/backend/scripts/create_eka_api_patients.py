#!/usr/bin/env python3
"""
Script to create patients directly using the Eka Care API
"""

import os
import json
import random
import sys
import requests
from datetime import datetime, date
from pathlib import Path
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

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune",
    "Kolkata", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kanpur"
]

STATES = {
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Bangalore": "Karnataka",
    "Chennai": "Tamil Nadu",
    "Hyderabad": "Telangana",
    "Pune": "Maharashtra",
    "Kolkata": "West Bengal",
    "Ahmedabad": "Gujarat",
    "Jaipur": "Rajasthan",
    "Surat": "Gujarat",
    "Lucknow": "Uttar Pradesh",
    "Kanpur": "Uttar Pradesh"
}

PINCODES = {
    "Mumbai": 400001,
    "Delhi": 110001,
    "Bangalore": 560001,
    "Chennai": 600001,
    "Hyderabad": 500001,
    "Pune": 411001,
    "Kolkata": 700001,
    "Ahmedabad": 380001,
    "Jaipur": 302001,
    "Surat": 395001,
    "Lucknow": 226001,
    "Kanpur": 208001
}

def generate_phone():
    """Generate a valid-looking Indian phone number"""
    prefix = random.choice(["9", "8", "7", "6"])
    rest = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return prefix + rest


def generate_random_date(start_year=1950, end_year=2005):
    """Generate a random date of birth"""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Simplified to avoid month-specific logic
    return date(year, month, day)


def generate_patient_payload():
    """Generate patient data for Eka Care API"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = random.choice(["M", "F"])  # Eka Care uses M/F format
    
    dob = generate_random_date()
    dob_str = dob.strftime("%Y-%m-%d")
    
    city = random.choice(list(CITIES))
    state = STATES.get(city, "Maharashtra")
    pincode = PINCODES.get(city, 400001)
    
    phone_number = generate_phone()
    
    # Generate a unique patient ID based on timestamp
    partner_patient_id = f"MF{int(datetime.now().timestamp())}"
    
    # Create payload for Eka Care API
    payload = {
        "dob": dob_str,
        "designation": "Mr." if gender == "M" else "Ms.",
        "first_name": first_name,
        "partner_patient_id": partner_patient_id,
        "middle_name": "",
        "last_name": last_name,
        "mobile": f"+91{phone_number}",
        "gender": gender,
        "address": {
            "city": city,
            "line1": f"{random.randint(1, 100)} {last_name} Apartments",
            "line2": f"{random.choice(['Sector', 'Block', 'Phase'])} {random.randint(1, 10)}",
            "pincode": pincode,
            "state": state,
            "country": "India"
        },
        "partner_meta": {"source": "MediFox_Demo"}
    }
    
    return payload


def get_auth_token():
    """Get authentication token using client credentials"""
    try:
        # Load environment variables
        load_dotenv()
        
        client_id = os.environ.get("EKA_CLIENT_ID")
        client_secret = os.environ.get("EKA_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            print("Error: EKA_CLIENT_ID or EKA_CLIENT_SECRET not set in environment")
            return None
            
        # Get authorization token
        auth_url = "https://dev.eka.care/api/v1/auth/login"
        auth_payload = {
            "client_id": client_id, 
            "client_secret": client_secret
        }
        
        auth_response = requests.post(auth_url, json=auth_payload)
        
        if auth_response.status_code != 200:
            print(f"Authentication failed: {auth_response.status_code} - {auth_response.text}")
            return None
            
        auth_data = auth_response.json()
        return f"{auth_data['token_type']} {auth_data['access_token']}"
    
    except Exception as e:
        print(f"Error getting authentication token: {e}")
        return None


def create_patient_in_eka_care(auth_token, patient_payload):
    """Create patient using Eka Care API"""
    try:
        url = "https://api.eka.care/dr/v1/patient"
        headers = {
            "Authorization": auth_token,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=patient_payload, headers=headers)
        
        if response.status_code == 201 or response.status_code == 200:
            print(f"Successfully created patient in Eka Care")
            return response.json()
        else:
            print(f"Failed to create patient: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating patient: {e}")
        return None


def save_patient_locally(patient_data, eka_response):
    """Save the patient data and Eka Care response locally"""
    try:
        # Create data directory if it doesn't exist
        data_dir = Path(__file__).parent.parent / "data" / "patients"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create combined data
        combined_data = {
            "patient_data": patient_data,
            "eka_response": eka_response,
            "created_at": datetime.now().isoformat()
        }
        
        # Use partner_patient_id for filename
        patient_id = patient_data["partner_patient_id"]
        patient_file = data_dir / f"{patient_id}.json"
        
        with open(patient_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
            
        print(f"Successfully saved patient data locally at {patient_file}")
        return True
        
    except Exception as e:
        print(f"Error saving patient data locally: {e}")
        return False


def main():
    """Main function to create patients in Eka Care"""
    print("Creating patients using Eka Care API...")
    
    # Get authentication token
    auth_token = get_auth_token()
    if not auth_token:
        print("Failed to get authentication token. Exiting.")
        return
    
    # Use default value for number of patients
    num_patients = 1  # Default to creating 1 patient
    try:
        num_arg = sys.argv[1] if len(sys.argv) > 1 else "1"
        num_patients = min(5, max(1, int(num_arg)))  # Limit between 1-5 patients
    except (ValueError, IndexError):
        pass

    print(f"\nCreating {num_patients} patient(s) in Eka Care...\n")
    
    # Keep track of all created patients
    created_patients = []
    
    for i in range(num_patients):
        print(f"\n--- Creating Patient {i+1}/{num_patients} ---")
        
        # Generate patient payload
        patient_payload = generate_patient_payload()
        
        print(f"Patient Name: {patient_payload['first_name']} {patient_payload['last_name']}")
        print(f"Patient ID: {patient_payload['partner_patient_id']}")
        print(f"Mobile: {patient_payload['mobile']}")
        
        # Create patient in Eka Care
        eka_response = create_patient_in_eka_care(auth_token, patient_payload)
        
        if eka_response:
            # Save locally
            save_patient_locally(patient_payload, eka_response)
            
            # Add to created patients list
            eka_patient_id = eka_response.get("data", {}).get("id", "unknown")
            
            created_patients.append({
                "partner_id": patient_payload["partner_patient_id"],
                "eka_id": eka_patient_id,
                "name": f"{patient_payload['first_name']} {patient_payload['last_name']}",
                "mobile": patient_payload["mobile"]
            })
    
    # Print summary
    if created_patients:
        print("\n" + "="*60)
        print(f"{len(created_patients)} PATIENT(S) CREATED IN EKA CARE")
        print("="*60)
        
        for i, patient in enumerate(created_patients):
            print(f"Patient #{i+1}:")
            print(f"  Name: {patient['name']}")
            print(f"  Partner ID: {patient['partner_id']}")
            print(f"  Eka Care ID: {patient['eka_id']}")
            print(f"  Mobile: {patient['mobile']}")
            print()
        
        # Save reference file
        try:
            reference_file = Path(__file__).parent / "eka_patients_reference.json"
            with open(reference_file, 'w') as f:
                json.dump({
                    "created_at": datetime.now().isoformat(),
                    "patients": created_patients
                }, f, indent=2)
            print(f"Reference file created at {reference_file}")
        except Exception as e:
            print(f"Failed to create reference file: {e}")
    else:
        print("\nNo patients were created in Eka Care.")


if __name__ == "__main__":
    main()
