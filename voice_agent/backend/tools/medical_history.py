from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

from .base_tool import BaseTool


class MedicalHistoryTool(BaseTool):
    """Tool for accessing and updating patient medical history."""
    
    def __init__(self):
        super().__init__(
            name="manage_medical_history",
            description="Access or update patient medical history including past conditions, surgeries, allergies, and chronic conditions"
        )
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "medical_records")
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Get or update patient medical history.
        
        Args:
            args: Dictionary with keys:
                - patient_id: ID of the patient
                - action: "get", "update", or "add_record"
                - category: For update/add: "conditions", "surgeries", "allergies", "medications", etc.
                - record: For update/add: The record to add
            context: Conversation context
            
        Returns:
            Dictionary with medical history data or confirmation
        """
        patient_id = args.get("patient_id")
        action = args.get("action", "get")
        
        if not patient_id:
            return {"error": "No patient ID provided"}
        
        history_file = os.path.join(self.data_dir, f"{patient_id}_history.json")
        
        # Get medical history
        if action == "get":
            if not os.path.exists(history_file):
                return {
                    "found": False,
                    "message": "No medical history found for this patient.",
                    "categories": [
                        "conditions", "surgeries", "allergies", 
                        "medications", "immunizations", "family_history"
                    ]
                }
            
            with open(history_file, 'r') as f:
                history_data = json.load(f)
                
            return {
                "found": True,
                "data": history_data
            }
            
        # Update medical history category
        elif action == "update":
            category = args.get("category")
            updated_records = args.get("records", [])
            
            if not category:
                return {"error": "No category specified for update"}
                
            # Create or load history file
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
            else:
                history_data = {
                    "patient_id": patient_id,
                    "conditions": [],
                    "surgeries": [],
                    "allergies": [],
                    "medications": [],
                    "immunizations": [],
                    "family_history": [],
                    "created_at": datetime.now().isoformat()
                }
            
            # Replace the entire category with new records
            history_data[category] = updated_records
            history_data["updated_at"] = datetime.now().isoformat()
            
            # Save back to file
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
            return {
                "success": True,
                "message": f"Medical history {category} updated",
                "data": history_data[category]
            }
                
        # Add a single record to a category
        elif action == "add_record":
            category = args.get("category")
            record = args.get("record", {})
            
            if not category or not record:
                return {"error": "Category and record are required for add_record"}
                
            # Create or load history file
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
            else:
                history_data = {
                    "patient_id": patient_id,
                    "conditions": [],
                    "surgeries": [],
                    "allergies": [],
                    "medications": [],
                    "immunizations": [],
                    "family_history": [],
                    "created_at": datetime.now().isoformat()
                }
            
            # Add record with timestamp
            if not history_data.get(category):
                history_data[category] = []
                
            # Add timestamp to the record
            if isinstance(record, dict):
                record["recorded_at"] = datetime.now().isoformat()
                
            history_data[category].append(record)
            history_data["updated_at"] = datetime.now().isoformat()
            
            # Save back to file
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
                
            return {
                "success": True,
                "message": f"Record added to {category}",
                "data": record
            }
            
        return {"error": "Invalid action. Use 'get', 'update', or 'add_record'."}
    
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
                            "enum": ["get", "update", "add_record"],
                            "description": "Whether to get existing history, update a category, or add a single record"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["conditions", "surgeries", "allergies", "medications", "immunizations", "family_history"],
                            "description": "The category of medical history to update or add to"
                        },
                        "records": {
                            "type": "array",
                            "description": "For update action: array of records to replace the entire category"
                        },
                        "record": {
                            "type": "object",
                            "description": "For add_record action: single record to add to a category"
                        }
                    },
                    "required": ["patient_id", "action"]
                }
            }
        }
