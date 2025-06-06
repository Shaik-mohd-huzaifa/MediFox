from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime, timedelta

from .base_tool import BaseTool
from ..integrations.eka_care_client import EkaCareClient


class AppointmentSchedulingTool(BaseTool):
    """Tool for managing healthcare appointments."""
    
    def __init__(self):
        super().__init__(
            name="manage_appointments",
            description="Schedule, reschedule, or cancel healthcare appointments"
        )
        # Initialize Eka Care client
        self.eka_client = EkaCareClient()
        
        # Keep local cache directory for fallback
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "appointments")
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Manage patient appointments.
        
        Args:
            args: Dictionary with keys:
                - patient_id: ID of the patient
                - action: "get", "schedule", "reschedule", "cancel"
                - appointment_id: ID of appointment (for reschedule/cancel)
                - details: Appointment details (for schedule/reschedule)
                - date_range: Optional date range for getting appointments
            context: Conversation context
            
        Returns:
            Dictionary with appointments or confirmation
        """
        patient_id = args.get("patient_id")
        action = args.get("action", "get")
        
        if not patient_id:
            return {"error": "No patient ID provided"}
        
        appt_file = os.path.join(self.data_dir, f"{patient_id}_appointments.json")
        
        # Get appointments
        if action == "get":
            try:
                # Try to get appointments from Eka Care
                doctor_id = args.get("doctor_id")  # Optional filter by doctor
                appointment_date = args.get("date")
                
                if not appointment_date:
                    # If no date provided, default to today
                    appointment_date = datetime.now().strftime("%Y-%m-%d")
                
                # Get appointment data from Eka Care
                if doctor_id:
                    eka_response = await self.eka_client.get_appointment_slots(
                        doctor_id=doctor_id,
                        date=appointment_date
                    )
                    
                    if eka_response and "data" in eka_response:
                        # Map Eka Care appointments to our format
                        appointments = [self._map_eka_slot_to_internal(slot) for slot in eka_response["data"]]
                        
                        return {
                            "found": len(appointments) > 0,
                            "appointments": appointments,
                            "source": "eka_care",
                            "date": appointment_date,
                            "doctor_id": doctor_id
                        }
                
                # If we don't have a doctor_id, try to get patient's existing appointments
                if patient_id:
                    # Note: This is a placeholder. The Eka Care API docs provided don't show a clear
                    # endpoint for getting a patient's appointments. In a real implementation,
                    # you would use the appropriate endpoint.
                    # For now, we'll fall back to local data.
                    pass
                
                # Fall back to local storage
                if os.path.exists(appt_file):
                    with open(appt_file, 'r') as f:
                        appt_data = json.load(f)
                    
                    # Filter by date range if provided
                    date_range = args.get("date_range")
                    if date_range:
                        start_date = datetime.fromisoformat(date_range.get("start", "2000-01-01T00:00:00"))
                        end_date = datetime.fromisoformat(date_range.get("end", "2100-01-01T00:00:00"))
                        
                        filtered_appointments = []
                        for appt in appt_data["appointments"]:
                            appt_date = datetime.fromisoformat(appt.get("datetime", "2000-01-01T00:00:00"))
                            if start_date <= appt_date <= end_date:
                                filtered_appointments.append(appt)
                                
                        return {
                            "found": len(filtered_appointments) > 0,
                            "appointments": filtered_appointments,
                            "filtered": True,
                            "source": "local_storage",
                            "total_count": len(appt_data["appointments"])
                        }
                    
                    # Return all appointments sorted by date
                    sorted_appointments = sorted(
                        appt_data["appointments"], 
                        key=lambda x: x.get("datetime", "2100-01-01T00:00:00")
                    )
                    
                    # Identify upcoming appointments
                    now = datetime.now()
                    for appt in sorted_appointments:
                        appt_date = datetime.fromisoformat(appt.get("datetime", "2100-01-01T00:00:00"))
                        appt["is_upcoming"] = appt_date > now
                        appt["days_away"] = (appt_date - now).days if appt_date > now else None
                    
                    return {
                        "found": True,
                        "appointments": sorted_appointments,
                        "source": "local_storage"
                    }
                    
                return {
                    "found": False,
                    "message": "No appointments found for this patient",
                    "appointments": []
                }
                    
            except Exception as e:
                print(f"Error getting appointments from Eka Care: {e}")
                
                # Fall back to local storage
                if os.path.exists(appt_file):
                    with open(appt_file, 'r') as f:
                        appt_data = json.load(f)
                    
                    return {
                        "found": True,
                        "appointments": appt_data["appointments"],
                        "source": "local_storage (fallback)",
                        "error": str(e)
                    }
                    
                return {
                    "found": False,
                    "message": "No appointments found for this patient",
                    "appointments": [],
                    "error": str(e)
                }
            
        # Schedule new appointment
        elif action == "schedule":
            details = args.get("details", {})
            
            if not details or not details.get("datetime") or not details.get("doctor_id"):
                return {"error": "Appointment details must include datetime and doctor_id"}
            
            try:
                # Map our appointment details to Eka Care format
                slot_id = details.get("slot_id")
                doctor_id = details.get("doctor_id")
                appointment_date = details.get("date")
                appointment_time = details.get("time")
                
                if not slot_id and (not doctor_id or not appointment_date or not appointment_time):
                    return {"error": "Appointment requires either a slot_id or doctor_id, date, and time"}
                
                # Prepare appointment data for Eka Care
                eka_appt_data = {
                    "patient_id": patient_id,
                }
                
                if slot_id:
                    eka_appt_data["slot_id"] = slot_id
                else:
                    # Combine date and time
                    eka_appt_data["doctor_id"] = doctor_id
                    eka_appt_data["appointment_date"] = appointment_date
                    eka_appt_data["appointment_time"] = appointment_time
                
                # Add any additional details provided
                if "reason" in details:
                    eka_appt_data["reason"] = details["reason"]
                if "notes" in details:
                    eka_appt_data["notes"] = details["notes"]
                
                # Book appointment with Eka Care
                eka_response = await self.eka_client.book_appointment(eka_appt_data)
                
                if eka_response and "data" in eka_response:
                    # Map the response to our format
                    new_appt = self._map_eka_appointment_to_internal(eka_response["data"])
                    
                    # Also update local cache
                    if os.path.exists(appt_file):
                        with open(appt_file, 'r') as f:
                            appt_data = json.load(f)
                    else:
                        appt_data = {
                            "patient_id": patient_id,
                            "appointments": [],
                            "created_at": datetime.now().isoformat()
                        }
                    
                    appt_data["appointments"].append(new_appt)
                    appt_data["updated_at"] = datetime.now().isoformat()
                    
                    with open(appt_file, 'w') as f:
                        json.dump(appt_data, f, indent=2)
                    
                    return {
                        "success": True,
                        "message": "Appointment scheduled with Eka Care",
                        "appointment": new_appt,
                        "source": "eka_care"
                    }
                    
                raise Exception("Failed to schedule appointment with Eka Care")
                    
            except Exception as e:
                print(f"Error scheduling appointment with Eka Care: {e}")
                
                # Fall back to local storage
                if os.path.exists(appt_file):
                    with open(appt_file, 'r') as f:
                        appt_data = json.load(f)
                else:
                    appt_data = {
                        "patient_id": patient_id,
                        "appointments": [],
                        "created_at": datetime.now().isoformat()
                    }
                
                # Generate appointment ID
                appt_id = f"appt_{len(appt_data['appointments']) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Add appointment details
                new_appt = {
                    "id": appt_id,
                    "status": "scheduled",
                    "created_at": datetime.now().isoformat(),
                    **details
                }
                
                appt_data["appointments"].append(new_appt)
                appt_data["updated_at"] = datetime.now().isoformat()
                
                # Save back to file
                with open(appt_file, 'w') as f:
                    json.dump(appt_data, f, indent=2)
                    
                return {
                    "success": True,
                    "message": "Appointment scheduled locally (Eka Care booking failed)",
                    "appointment": new_appt,
                    "source": "local_storage",
                    "warning": f"Failed to book with Eka Care: {str(e)}"
                }
                
        # Reschedule existing appointment
        elif action == "reschedule":
            appointment_id = args.get("appointment_id")
            details = args.get("details", {})
            
            if not appointment_id or not details:
                return {"error": "Appointment ID and new details are required"}
            
            try:
                # Try to retrieve the existing appointment details from Eka Care
                # Note: Implement this once Eka Care API has a method for getting appointment details
                # For now, we'll assume we need to know the doctor_id, date, and time for rescheduling
                
                # Required fields for rescheduling
                slot_id = details.get("slot_id")
                doctor_id = details.get("doctor_id")
                appointment_date = details.get("date")
                appointment_time = details.get("time")
                
                if not slot_id and (not doctor_id or not appointment_date or not appointment_time):
                    return {"error": "Rescheduling requires either a slot_id or doctor_id, date, and time"}
                
                # Prepare rescheduling data for Eka Care
                eka_reschedule_data = {
                    "appointment_id": appointment_id
                }
                
                if slot_id:
                    eka_reschedule_data["slot_id"] = slot_id
                else:
                    eka_reschedule_data["doctor_id"] = doctor_id
                    eka_reschedule_data["appointment_date"] = appointment_date
                    eka_reschedule_data["appointment_time"] = appointment_time
                
                # Add any additional details provided
                if "reason" in details:
                    eka_reschedule_data["reason"] = details["reason"]
                if "notes" in details:
                    eka_reschedule_data["notes"] = details["notes"]
                
                # Call Eka Care API to reschedule the appointment
                # Note: We're assuming there's a reschedule_appointment method in the Eka Care client
                # You may need to implement this method if it doesn't exist
                eka_response = await self.eka_client.reschedule_appointment(eka_reschedule_data)
                
                if eka_response and "data" in eka_response:
                    # Map the response to our format
                    rescheduled_appt = self._map_eka_appointment_to_internal(eka_response["data"])
                    
                    # Also update local cache if it exists
                    if os.path.exists(appt_file):
                        with open(appt_file, 'r') as f:
                            appt_data = json.load(f)
                        
                        # Find and update the appointment in local data
                        for appt in appt_data["appointments"]:
                            if appt.get("id") == appointment_id or appt.get("eka_id") == appointment_id:
                                # Store previous datetime for reference
                                prev_datetime = appt.get("datetime")
                                
                                # Update fields from the rescheduled appointment
                                for key, value in rescheduled_appt.items():
                                    # Don't override the ID to maintain local tracking
                                    if key != "id":
                                        appt[key] = value
                                
                                # Mark as rescheduled
                                appt["status"] = "rescheduled"
                                appt["previous_datetime"] = prev_datetime
                                appt["rescheduled_at"] = datetime.now().isoformat()
                                break
                        
                        # Save back to file
                        appt_data["updated_at"] = datetime.now().isoformat()
                        with open(appt_file, 'w') as f:
                            json.dump(appt_data, f, indent=2)
                    
                    return {
                        "success": True,
                        "message": "Appointment rescheduled with Eka Care",
                        "appointment": rescheduled_appt,
                        "source": "eka_care"
                    }
                
                raise Exception("Failed to reschedule appointment with Eka Care")
                
            except Exception as e:
                print(f"Error rescheduling appointment with Eka Care: {e}")
                
                # Fall back to local storage
                # Check if appointments file exists
                if os.path.exists(appt_file):
                    # Load appointments
                    with open(appt_file, 'r') as f:
                        appt_data = json.load(f)
                    
                    # Find and update the appointment
                    for appt in appt_data["appointments"]:
                        if appt.get("id") == appointment_id:
                            # Store previous datetime for reference
                            prev_datetime = appt.get("datetime")
                            
                            # Update fields
                            for key, value in details.items():
                                appt[key] = value
                            
                            # Mark as rescheduled
                            appt["status"] = "rescheduled"
                            appt["previous_datetime"] = prev_datetime
                            appt["rescheduled_at"] = datetime.now().isoformat()
                            
                            # Save back to file
                            appt_data["updated_at"] = datetime.now().isoformat()
                            with open(appt_file, 'w') as f:
                                json.dump(appt_data, f, indent=2)
                                
                            return {
                                "success": True,
                                "message": "Appointment rescheduled locally (Eka Care rescheduling failed)",
                                "appointment": appt,
                                "source": "local_storage",
                                "warning": f"Failed to reschedule with Eka Care: {str(e)}"
                            }
                    
                    return {"error": "Appointment not found in local storage"}
                    
                return {"error": "No appointments found for this patient"}
            
        # Cancel appointment
        elif action == "cancel":
            appointment_id = args.get("appointment_id")
            reason = args.get("reason", "No reason provided")
            
            if not appointment_id:
                return {"error": "Appointment ID is required"}
            
            try:
                # Try to cancel appointment in Eka Care
                eka_response = await self.eka_client.cancel_appointment(appointment_id, reason)
                
                if eka_response and "data" in eka_response:
                    # Map the response to our format
                    cancelled_appt = self._map_eka_appointment_to_internal(eka_response["data"])
                    
                    # Also update local cache if it exists
                    if os.path.exists(appt_file):
                        with open(appt_file, 'r') as f:
                            appt_data = json.load(f)
                            
                        # Find and update the appointment in local data
                        for appt in appt_data["appointments"]:
                            if appt.get("id") == appointment_id or appt.get("eka_id") == appointment_id:
                                appt["status"] = "cancelled"
                                appt["cancellation_reason"] = reason
                                appt["cancelled_at"] = datetime.now().isoformat()
                                
                        # Save back to file
                        appt_data["updated_at"] = datetime.now().isoformat()
                        with open(appt_file, 'w') as f:
                            json.dump(appt_data, f, indent=2)
                    
                    return {
                        "success": True,
                        "message": "Appointment cancelled in Eka Care",
                        "appointment": cancelled_appt,
                        "source": "eka_care"
                    }
                    
                raise Exception("Failed to cancel appointment in Eka Care")
                
            except Exception as e:
                print(f"Error cancelling appointment in Eka Care: {e}")
                
                # Fall back to local storage
                # Check if appointments file exists
                if os.path.exists(appt_file):
                    # Load appointments
                    with open(appt_file, 'r') as f:
                        appt_data = json.load(f)
                    
                    # Find and cancel the appointment
                    for appt in appt_data["appointments"]:
                        if appt.get("id") == appointment_id:
                            # Mark as cancelled
                            appt["status"] = "cancelled"
                            appt["cancellation_reason"] = reason
                            appt["cancelled_at"] = datetime.now().isoformat()
                            
                            # Save back to file
                            appt_data["updated_at"] = datetime.now().isoformat()
                            with open(appt_file, 'w') as f:
                                json.dump(appt_data, f, indent=2)
                                
                            return {
                                "success": True,
                                "message": "Appointment cancelled locally (Eka Care cancellation failed)",
                                "appointment": appt,
                                "source": "local_storage",
                                "warning": f"Failed to cancel in Eka Care: {str(e)}"
                            }
                    
                    return {"error": "Appointment not found in local storage"}
                    
                return {"error": "No appointments found for this patient"}
            
        return {"error": "Invalid action"}
    
    def _map_eka_slot_to_internal(self, slot_data: Dict) -> Dict:
        """
        Maps an Eka Care appointment slot to our internal format
        """
        # This is a placeholder mapping function - adjust according to actual Eka Care API response
        return {
            "id": slot_data.get("id"),
            "eka_id": slot_data.get("id"),  # Store original Eka Care ID separately
            "slot_id": slot_data.get("slot_id"),
            "doctor_id": slot_data.get("doctor_id"),
            "doctor_name": slot_data.get("doctor_name", ""),
            "date": slot_data.get("date"),
            "time": slot_data.get("time"),
            "datetime": f"{slot_data.get('date')}T{slot_data.get('time')}",
            "duration": slot_data.get("duration", 15),  # Default 15 min if not specified
            "provider": {
                "id": slot_data.get("doctor_id"),
                "name": slot_data.get("doctor_name", ""),
                "specialty": slot_data.get("specialty", ""),
            },
            "facility": slot_data.get("facility", {}),
            "status": "available",
            "source": "eka_care"
        }

    def _map_eka_appointment_to_internal(self, appt_data: Dict) -> Dict:
        """
        Maps an Eka Care appointment to our internal format
        """
        # This is a placeholder mapping function - adjust according to actual Eka Care API response
        return {
            "id": appt_data.get("id"),
            "eka_id": appt_data.get("id"),  # Store original Eka Care ID separately
            "patient_id": appt_data.get("patient_id"),
            "doctor_id": appt_data.get("doctor_id"),
            "doctor_name": appt_data.get("doctor_name", ""),
            "date": appt_data.get("date"),
            "time": appt_data.get("time"),
            "datetime": f"{appt_data.get('date')}T{appt_data.get('time')}",
            "duration": appt_data.get("duration", 15),
            "provider": {
                "id": appt_data.get("doctor_id"),
                "name": appt_data.get("doctor_name", ""),
                "specialty": appt_data.get("specialty", "")
            },
            "reason": appt_data.get("reason", ""),
            "notes": appt_data.get("notes", ""),
            "status": appt_data.get("status", "scheduled"),
            "created_at": appt_data.get("created_at", datetime.now().isoformat()),
            "source": "eka_care"
        }

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
                            "description": "ID of the patient"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["get", "schedule", "reschedule", "cancel"],
                            "description": "Action to perform: get appointments, schedule, reschedule, or cancel"
                        },
                        "doctor_id": {
                            "type": "string",
                            "description": "ID of the doctor (for getting available slots or scheduling appointments)"
                        },
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (for getting available slots or scheduling)"
                        },
                        "appointment_id": {
                            "type": "string",
                            "description": "ID of appointment for reschedule/cancel operations"
                        },
                        "details": {
                            "type": "object",
                            "properties": {
                                "doctor_id": {
                                    "type": "string",
                                    "description": "ID of the doctor"
                                },
                                "slot_id": {
                                    "type": "string",
                                    "description": "ID of the appointment slot in Eka Care"
                                },
                                "date": {
                                    "type": "string",
                                    "description": "Date in YYYY-MM-DD format"
                                },
                                "time": {
                                    "type": "string",
                                    "description": "Time in HH:MM format"
                                },
                                "datetime": {
                                    "type": "string",
                                    "description": "ISO format datetime for the appointment"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "Reason for the appointment"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Additional notes for the appointment"
                                }
                            },
                            "description": "Appointment details for scheduling or rescheduling"
                        },
                        "date_range": {
                            "type": "object",
                            "properties": {
                                "start": {"type": "string", "description": "Start date (ISO format)"},
                                "end": {"type": "string", "description": "End date (ISO format)"}
                            },
                            "description": "Optional date range for filtering appointments"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation"
                        }
                    },
                    "required": ["patient_id", "action"]
                }
            }
        }
