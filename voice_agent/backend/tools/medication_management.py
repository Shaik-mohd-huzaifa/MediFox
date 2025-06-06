from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime, timedelta

from .base_tool import BaseTool


class MedicationManagementTool(BaseTool):
    """Tool for managing patient medications and prescriptions."""
    
    def __init__(self):
        super().__init__(
            name="manage_medications",
            description="Track prescriptions, medication schedules, and provide dosage and interaction information"
        )
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "medications")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Simple database of common drug interactions
        # In a production system, this would be integrated with a comprehensive drug database
        self.drug_interactions = {
            "warfarin": ["aspirin", "ibuprofen", "naproxen", "clopidogrel", "fluconazole"],
            "simvastatin": ["clarithromycin", "itraconazole", "ketoconazole", "grapefruit juice"],
            "lisinopril": ["spironolactone", "potassium supplements", "lithium"],
            "metformin": ["contrast agents", "alcohol"],
            "levothyroxine": ["calcium", "iron", "antacids"],
        }
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Manage patient medications.
        
        Args:
            args: Dictionary with keys:
                - patient_id: ID of the patient
                - action: "get", "add", "update", "remove", "check_interactions", "generate_schedule"
                - medication: (for add/update) Medication details 
                - medication_id: (for update/remove) ID of the medication to update/remove
                - medications: (for check_interactions) List of medications to check
            context: Conversation context
            
        Returns:
            Dictionary with medication data or confirmation
        """
        patient_id = args.get("patient_id")
        action = args.get("action", "get")
        
        if not patient_id:
            return {"error": "No patient ID provided"}
        
        meds_file = os.path.join(self.data_dir, f"{patient_id}_medications.json")
        
        # Get current medications
        if action == "get":
            if not os.path.exists(meds_file):
                return {
                    "found": False,
                    "message": "No medications found for this patient.",
                    "medications": []
                }
            
            with open(meds_file, 'r') as f:
                meds_data = json.load(f)
                
            # Check for medications that need refills
            now = datetime.now()
            for med in meds_data["medications"]:
                if "end_date" in med:
                    end_date = datetime.fromisoformat(med["end_date"])
                    # If within 7 days of end date, flag for refill
                    if end_date - now <= timedelta(days=7):
                        med["needs_refill"] = True
                        med["days_until_refill"] = (end_date - now).days
                    else:
                        med["needs_refill"] = False
                
            return {
                "found": True,
                "medications": meds_data["medications"]
            }
            
        # Add new medication
        elif action == "add":
            medication = args.get("medication", {})
            
            if not medication or not medication.get("name"):
                return {"error": "Valid medication details required"}
                
            # Create or load medications file
            if os.path.exists(meds_file):
                with open(meds_file, 'r') as f:
                    meds_data = json.load(f)
            else:
                meds_data = {
                    "patient_id": patient_id,
                    "medications": [],
                    "created_at": datetime.now().isoformat()
                }
            
            # Generate medication ID
            med_id = f"med_{len(meds_data['medications']) + 1}_{medication['name'].lower().replace(' ', '_')}"
            
            # Add additional fields
            medication["id"] = med_id
            medication["added_on"] = datetime.now().isoformat()
            
            # Add medication to list
            meds_data["medications"].append(medication)
            meds_data["updated_at"] = datetime.now().isoformat()
            
            # Save back to file
            with open(meds_file, 'w') as f:
                json.dump(meds_data, f, indent=2)
                
            # Check for potential interactions
            interactions = self._check_interactions_for_med(medication["name"], meds_data["medications"])
            
            return {
                "success": True,
                "message": "Medication added",
                "medication": medication,
                "interactions": interactions
            }
                
        # Update existing medication
        elif action == "update":
            medication_id = args.get("medication_id")
            updated_info = args.get("medication", {})
            
            if not medication_id or not updated_info:
                return {"error": "Medication ID and updated details are required"}
                
            # Check if medications file exists
            if not os.path.exists(meds_file):
                return {"error": "No medications found for this patient"}
                
            # Load current medications
            with open(meds_file, 'r') as f:
                meds_data = json.load(f)
            
            # Find and update the medication
            for i, med in enumerate(meds_data["medications"]):
                if med.get("id") == medication_id:
                    # Update fields
                    for key, value in updated_info.items():
                        med[key] = value
                    
                    med["last_updated"] = datetime.now().isoformat()
                    
                    # Save back to file
                    meds_data["updated_at"] = datetime.now().isoformat()
                    with open(meds_file, 'w') as f:
                        json.dump(meds_data, f, indent=2)
                        
                    return {
                        "success": True,
                        "message": "Medication updated",
                        "medication": med
                    }
            
            return {"error": "Medication not found"}
            
        # Remove medication
        elif action == "remove":
            medication_id = args.get("medication_id")
            
            if not medication_id:
                return {"error": "Medication ID is required"}
                
            # Check if medications file exists
            if not os.path.exists(meds_file):
                return {"error": "No medications found for this patient"}
                
            # Load current medications
            with open(meds_file, 'r') as f:
                meds_data = json.load(f)
            
            # Find and remove the medication
            for i, med in enumerate(meds_data["medications"]):
                if med.get("id") == medication_id:
                    removed_med = meds_data["medications"].pop(i)
                    
                    # Save back to file
                    meds_data["updated_at"] = datetime.now().isoformat()
                    with open(meds_file, 'w') as f:
                        json.dump(meds_data, f, indent=2)
                        
                    return {
                        "success": True,
                        "message": "Medication removed",
                        "removed": removed_med
                    }
            
            return {"error": "Medication not found"}
            
        # Check for drug interactions
        elif action == "check_interactions":
            medications = args.get("medications", [])
            
            if not medications:
                # If no medications provided, load from file if available
                if os.path.exists(meds_file):
                    with open(meds_file, 'r') as f:
                        meds_data = json.load(f)
                    medications = [med.get("name", "").lower() for med in meds_data["medications"]]
                else:
                    return {"error": "No medications provided or found for this patient"}
            
            # Normalize medication names to lowercase
            medications = [med.lower() if isinstance(med, str) else med.get("name", "").lower() for med in medications]
            
            # Check for interactions
            interactions = []
            for i, med1 in enumerate(medications):
                for med2 in medications[i+1:]:
                    if med1 in self.drug_interactions and med2 in self.drug_interactions[med1]:
                        interactions.append(f"{med1} interacts with {med2}")
                    elif med2 in self.drug_interactions and med1 in self.drug_interactions[med2]:
                        interactions.append(f"{med2} interacts with {med1}")
            
            return {
                "interactions_found": len(interactions) > 0,
                "interactions": interactions,
                "medications_checked": medications
            }
            
        # Generate medication schedule
        elif action == "generate_schedule":
            if not os.path.exists(meds_file):
                return {"error": "No medications found for this patient"}
                
            with open(meds_file, 'r') as f:
                meds_data = json.load(f)
            
            # Group medications by time of day
            schedule = {
                "morning": [],
                "afternoon": [],
                "evening": [],
                "bedtime": [],
                "as_needed": []
            }
            
            for med in meds_data["medications"]:
                if "frequency" not in med:
                    continue
                    
                freq = med["frequency"].lower()
                name = med.get("name", "")
                dosage = med.get("dosage", "")
                instructions = med.get("instructions", "")
                
                # Add to appropriate time slots
                if "morning" in freq or "breakfast" in freq or "am" in freq:
                    schedule["morning"].append(f"{name} {dosage} {instructions}")
                if "afternoon" in freq or "lunch" in freq or "noon" in freq:
                    schedule["afternoon"].append(f"{name} {dosage} {instructions}")
                if "evening" in freq or "dinner" in freq or "pm" in freq:
                    schedule["evening"].append(f"{name} {dosage} {instructions}")
                if "bedtime" in freq or "night" in freq:
                    schedule["bedtime"].append(f"{name} {dosage} {instructions}")
                if "as needed" in freq or "prn" in freq:
                    schedule["as_needed"].append(f"{name} {dosage} {instructions}")
            
            return {
                "daily_schedule": schedule,
                "medication_count": len(meds_data["medications"])
            }
            
        return {"error": "Invalid action"}
    
    def _check_interactions_for_med(self, new_med: str, current_meds: List[Dict]) -> List[str]:
        """Check if a new medication interacts with any current medications."""
        interactions = []
        new_med_lower = new_med.lower()
        
        for med in current_meds:
            med_name = med.get("name", "").lower()
            if med_name == new_med_lower:
                continue  # Skip comparing with itself
                
            if new_med_lower in self.drug_interactions and med_name in self.drug_interactions[new_med_lower]:
                interactions.append(f"{new_med} interacts with {med['name']}")
                
            if med_name in self.drug_interactions and new_med_lower in self.drug_interactions[med_name]:
                interactions.append(f"{med['name']} interacts with {new_med}")
        
        return interactions
    
    def get_schema(self) -> Dict[str, Any]:
        """Returns the schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "The unique identifier for the patient"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "add", "update", "remove", "check_interactions", "generate_schedule"],
                            "description": "The action to perform on medications"
                        },
                        "medication": {
                            "type": "object",
                            "description": "For add/update: Object with medication details including name, dosage, frequency, etc."
                        },
                        "medication_id": {
                            "type": "string",
                            "description": "For update/remove: ID of the medication to update or remove"
                        },
                        "medications": {
                            "type": "array",
                            "description": "For check_interactions: List of medication names to check for interactions"
                        }
                    },
                    "required": ["patient_id", "action"]
                }
            }
        }
