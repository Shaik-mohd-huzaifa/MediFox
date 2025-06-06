from typing import Dict, Any, Optional, List
import os
from datetime import datetime

from .base_tool import BaseTool
from ..integrations.eka_care_client import EkaCareClient


class PatientInfoTool(BaseTool):
    """Tool for managing patient information."""
    
    def __init__(self):
        super().__init__(
            name="get_patient_info",
            description="Get or update patient personal and demographic information"
        )
        # Initialize Eka Care client
        self.eka_client = EkaCareClient()
        
        # Keep local cache directory for fallback
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "patients")
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Get or update patient information.
        
        Args:
            args: Dictionary with keys:
                - patient_id: ID of the patient
                - action: "get" or "update"
                - fields: (for update only) Dict of fields to update
            context: Conversation context
            
        Returns:
            Dictionary with patient information
        """
        patient_id = args.get("patient_id")
        action = args.get("action", "get")
        mobile_number = args.get("mobile_number")
        
        if not patient_id and not mobile_number:
            return {"error": "No patient ID or mobile number provided"}
        
        # Get patient info
        if action == "get":
            try:
                if patient_id:
                    # Get patient by ID from Eka Care
                    eka_response = await self.eka_client.get_patient_by_id(patient_id)
                    if eka_response and "data" in eka_response:
                        patient_data = self._map_eka_patient_to_internal(eka_response["data"])
                        return {
                            "found": True,
                            "data": patient_data,
                            "source": "eka_care"
                        }
                elif mobile_number:
                    # Search patient by mobile number
                    eka_response = await self.eka_client.search_patient_by_mobile(mobile_number)
                    if eka_response and "data" in eka_response and eka_response["data"]:
                        # If multiple patients found with the same number, return first one
                        patient_data = self._map_eka_patient_to_internal(eka_response["data"][0])
                        return {
                            "found": True,
                            "data": patient_data,
                            "source": "eka_care"
                        }
                    
                # Fall back to local storage if needed
                patient_file = os.path.join(self.data_dir, f"{patient_id or mobile_number}.json")
                if os.path.exists(patient_file):
                    with open(patient_file, 'r') as f:
                        import json
                        patient_data = json.load(f)
                        
                    # Check for missing required fields
                    required_fields = ["name", "age", "gender", "contact_number", "address"]
                    missing_fields = [field for field in required_fields if not patient_data.get(field)]
                    
                    return {
                        "found": True,
                        "data": patient_data,
                        "missing_fields": missing_fields,
                        "complete": len(missing_fields) == 0,
                        "source": "local_storage"
                    }
                    
                # Patient not found
                return {
                    "found": False,
                    "message": "Patient not found. Please collect basic information.",
                    "required_fields": [
                        "name", "age", "gender", "contact_number", 
                        "address", "emergency_contact", "blood_type"
                    ]
                }
                
            except Exception as e:
                # Log the error and fall back to local storage
                print(f"Error fetching patient from Eka Care: {e}")
                
                # Try local fallback
                patient_file = os.path.join(self.data_dir, f"{patient_id or mobile_number}.json")
                if os.path.exists(patient_file):
                    with open(patient_file, 'r') as f:
                        import json
                        patient_data = json.load(f)
                    return {
                        "found": True,
                        "data": patient_data,
                        "source": "local_storage (fallback)"
                    }
                    
                return {
                    "error": f"Failed to retrieve patient information: {str(e)}",
                    "found": False
                }
            
        # Update patient info
        elif action == "update":
            fields = args.get("fields", {})
            if not fields:
                return {"error": "No fields provided for update"}
            
            try:
                # First check if patient exists in Eka Care
                patient_exists = False
                eka_patient_id = None
                
                if patient_id:
                    # Try to get existing patient
                    try:
                        eka_response = await self.eka_client.get_patient_by_id(patient_id)
                        if eka_response and "data" in eka_response:
                            patient_exists = True
                            eka_patient_id = patient_id
                    except:
                        pass  # Patient doesn't exist, we'll create a new one
                elif mobile_number:
                    # Try to find by mobile
                    try:
                        eka_response = await self.eka_client.search_patient_by_mobile(mobile_number)
                        if eka_response and "data" in eka_response and eka_response["data"]:
                            patient_exists = True
                            eka_patient_id = eka_response["data"][0].get("id")
                    except:
                        pass  # Patient doesn't exist, we'll create a new one
                
                # Map our fields to Eka Care format
                eka_patient_data = self._map_internal_to_eka_patient(fields)
                
                # Add or update patient in Eka Care
                if patient_exists and eka_patient_id:
                    # Update existing patient
                    eka_patient_data["id"] = eka_patient_id
                    eka_response = await self.eka_client.update_patient(eka_patient_id, eka_patient_data)
                else:
                    # Create new patient
                    eka_response = await self.eka_client.add_patient(eka_patient_data)
                
                if eka_response and "data" in eka_response:
                    # Success - map response back to our format
                    updated_patient = self._map_eka_patient_to_internal(eka_response["data"])
                    
                    # Also update local cache
                    patient_file = os.path.join(self.data_dir, f"{updated_patient['id']}.json")
                    with open(patient_file, 'w') as f:
                        import json
                        json.dump(updated_patient, f, indent=2)
                    
                    return {
                        "success": True,
                        "message": "Patient information updated in Eka Care",
                        "data": updated_patient,
                        "eka_patient_id": updated_patient["id"]
                    }
                    
                # If we reach here, something went wrong with the API
                raise Exception("Failed to update patient in Eka Care")
                    
            except Exception as e:
                print(f"Error updating patient in Eka Care: {e}")
                
                # Fall back to local storage
                patient_file = os.path.join(self.data_dir, f"{patient_id or mobile_number}.json")
                
                # Create or update patient file
                if os.path.exists(patient_file):
                    with open(patient_file, 'r') as f:
                        import json
                        patient_data = json.load(f)
                else:
                    patient_data = {"id": patient_id or mobile_number, "created_at": datetime.now().isoformat()}
                
                # Update fields locally
                for key, value in fields.items():
                    patient_data[key] = value
                    
                # Add last updated timestamp
                patient_data["updated_at"] = datetime.now().isoformat()
                
                # Save back to file
                with open(patient_file, 'w') as f:
                    import json
                    json.dump(patient_data, f, indent=2)
                    
                return {
                    "success": True,
                    "message": "Patient information updated in local storage (Eka Care update failed)",
                    "data": patient_data,
                    "warning": f"Failed to update in Eka Care: {str(e)}"
                }
                
        return {"error": "Invalid action. Use 'get' or 'update'."}
    
    def _map_eka_patient_to_internal(self, eka_patient: Dict) -> Dict:
        """Map Eka Care patient data format to our internal format"""
        # Add field mapping based on Eka Care API response structure
        # This is a placeholder implementation - adjust based on actual Eka response format
        return {
            "id": eka_patient.get("id"),
            "name": eka_patient.get("name", ""),
            "age": eka_patient.get("age"),
            "gender": eka_patient.get("gender"),
            "contact_number": eka_patient.get("mobile"),
            "address": eka_patient.get("address", {}),
            "emergency_contact": eka_patient.get("emergency_contact"),
            "blood_type": eka_patient.get("blood_group"),
            "allergies": eka_patient.get("allergies"),
            "eka_data": eka_patient,  # Store the complete Eka data for reference
            "updated_at": datetime.now().isoformat()
        }
    
    def _map_internal_to_eka_patient(self, patient_data: Dict) -> Dict:
        """Map our internal patient data format to Eka Care format"""
        # This is a placeholder implementation - adjust based on actual Eka API requirements
        eka_patient = {
            "name": patient_data.get("name"),
            "gender": patient_data.get("gender"),
            "mobile": patient_data.get("contact_number"),
            "age": patient_data.get("age"),
            "blood_group": patient_data.get("blood_type"),
        }
        
        # Handle address if present
        if "address" in patient_data:
            if isinstance(patient_data["address"], dict):
                eka_patient["address"] = patient_data["address"]
            else:
                # If address is a string, convert to expected format
                eka_patient["address"] = {"full_address": patient_data["address"]}
        
        # Handle emergency contact if present
        if "emergency_contact" in patient_data:
            eka_patient["emergency_contact"] = patient_data["emergency_contact"]
            
        # Add any other required fields for Eka Care
        return eka_patient
    
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
                        "mobile_number": {
                            "type": "string",
                            "description": "Patient's mobile number to search by if ID is not known"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "update"],
                            "description": "Whether to get existing info or update with new info"
                        },
                        "fields": {
                            "type": "object",
                            "description": "For update action: fields to update and their new values"
                        }
                    },
                    "required": ["action"],
                    "anyOf": [
                        {"required": ["patient_id"]},
                        {"required": ["mobile_number"]}
                    ]
                }
            }
        }
