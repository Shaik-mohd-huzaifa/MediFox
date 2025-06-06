import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class MemoryManager:
    """
    Manages conversation memory and context for the MediFox healthcare agent.
    Provides persistent memory storage and retrieval functions.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize the memory manager.
        
        Args:
            storage_dir: Directory to store memory files (defaults to data/memory)
        """
        if not storage_dir:
            storage_dir = os.path.join(os.path.dirname(__file__), "data", "memory")
        
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def save_conversation(self, session_id: str, context: List[Dict[str, str]]) -> None:
        """
        Save the current conversation context to persistent storage.
        
        Args:
            session_id: The unique session identifier
            context: The conversation context to save
        """
        memory_file = os.path.join(self.storage_dir, f"{session_id}_memory.json")
        
        # Create memory entry with metadata
        memory_entry = {
            "session_id": session_id,
            "last_updated": datetime.now().isoformat(),
            "context": context
        }
        
        with open(memory_file, 'w') as f:
            json.dump(memory_entry, f, indent=2)
    
    def load_conversation(self, session_id: str) -> List[Dict[str, str]]:
        """
        Load a conversation context from persistent storage.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            The conversation context or an empty list if not found
        """
        memory_file = os.path.join(self.storage_dir, f"{session_id}_memory.json")
        
        if not os.path.exists(memory_file):
            return []
        
        with open(memory_file, 'r') as f:
            memory_entry = json.load(f)
            
        return memory_entry.get("context", [])
    
    def get_patient_context(self, patient_id: str) -> Dict[str, Any]:
        """
        Get aggregated patient context from various data sources.
        
        Args:
            patient_id: The unique patient identifier
            
        Returns:
            Dictionary with comprehensive patient context
        """
        patient_context = {
            "patient_id": patient_id,
            "info": self._get_patient_info(patient_id),
            "medical_history": self._get_patient_medical_history(patient_id),
            "appointments": self._get_patient_appointments(patient_id),
            "medications": self._get_patient_medications(patient_id)
        }
        
        return patient_context
    
    def _get_patient_info(self, patient_id: str) -> Dict[str, Any]:
        """Get basic patient info from storage."""
        patient_file = os.path.join(os.path.dirname(__file__), "data", "patients", f"{patient_id}.json")
        if os.path.exists(patient_file):
            with open(patient_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _get_patient_medical_history(self, patient_id: str) -> Dict[str, Any]:
        """Get patient medical history from storage."""
        history_file = os.path.join(os.path.dirname(__file__), "data", "medical_records", f"{patient_id}_history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient appointments from storage."""
        appt_file = os.path.join(os.path.dirname(__file__), "data", "appointments", f"{patient_id}_appointments.json")
        if os.path.exists(appt_file):
            with open(appt_file, 'r') as f:
                data = json.load(f)
                return data.get("appointments", [])
        return []
    
    def _get_patient_medications(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient medications from storage."""
        meds_file = os.path.join(os.path.dirname(__file__), "data", "medications", f"{patient_id}_medications.json")
        if os.path.exists(meds_file):
            with open(meds_file, 'r') as f:
                data = json.load(f)
                return data.get("medications", [])
        return []
    
    def summarize_patient_context(self, patient_id: str) -> str:
        """
        Generate a human-readable summary of patient context.
        
        Args:
            patient_id: The unique patient identifier
            
        Returns:
            String summary of patient information
        """
        context = self.get_patient_context(patient_id)
        
        # Basic patient info
        patient_info = context.get("info", {})
        if not patient_info:
            return f"No information found for patient ID: {patient_id}"
        
        summary_parts = []
        
        # Patient demographics
        name = patient_info.get("name", "Unknown")
        age = patient_info.get("age", "Unknown")
        gender = patient_info.get("gender", "Unknown")
        
        summary_parts.append(f"Patient: {name}, {age} year old {gender}")
        
        # Medical history summary
        medical_history = context.get("medical_history", {})
        if medical_history:
            conditions = medical_history.get("conditions", [])
            allergies = medical_history.get("allergies", [])
            
            if conditions:
                condition_names = [c.get("name", c) if isinstance(c, dict) else c for c in conditions]
                summary_parts.append(f"Conditions: {', '.join(condition_names)}")
            
            if allergies:
                allergy_names = [a.get("name", a) if isinstance(a, dict) else a for a in allergies]
                summary_parts.append(f"Allergies: {', '.join(allergy_names)}")
        
        # Medication summary
        medications = context.get("medications", [])
        if medications:
            med_names = [m.get("name", "Unknown") for m in medications]
            summary_parts.append(f"Current medications: {', '.join(med_names)}")
        
        # Upcoming appointments
        appointments = context.get("appointments", [])
        upcoming_appts = [a for a in appointments if a.get("status") == "scheduled"]
        if upcoming_appts:
            next_appt = upcoming_appts[0]
            provider = next_appt.get("provider", "Unknown provider")
            date = next_appt.get("datetime", "Unknown date")
            summary_parts.append(f"Next appointment: {date} with {provider}")
        
        return "\n".join(summary_parts)
