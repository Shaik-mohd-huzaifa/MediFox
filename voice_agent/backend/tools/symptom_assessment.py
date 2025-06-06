from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

from .base_tool import BaseTool


class SymptomAssessmentTool(BaseTool):
    """Tool for analyzing patient symptoms and providing assessments."""
    
    def __init__(self):
        super().__init__(
            name="assess_symptoms",
            description="Analyze reported symptoms, suggest possible diagnoses, and determine if immediate care is needed"
        )
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "symptom_records")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Simple mapping of common symptoms to possible conditions
        # In a production system, this would be a more sophisticated medical knowledge graph
        self.symptom_mapping = {
            "headache": [
                {"condition": "Tension Headache", "severity": "low", "flags": []},
                {"condition": "Migraine", "severity": "medium", "flags": []},
                {"condition": "Dehydration", "severity": "low", "flags": []},
                {"condition": "High Blood Pressure", "severity": "medium", "flags": ["check_bp"]},
                {"condition": "Meningitis", "severity": "high", "flags": ["urgent", "fever", "stiff_neck"]}
            ],
            "chest_pain": [
                {"condition": "Angina", "severity": "medium", "flags": ["check_cardiac"]},
                {"condition": "Heart Attack", "severity": "high", "flags": ["urgent", "emergency"]},
                {"condition": "Acid Reflux", "severity": "low", "flags": []},
                {"condition": "Muscle Strain", "severity": "low", "flags": []},
                {"condition": "Pulmonary Embolism", "severity": "high", "flags": ["urgent", "emergency"]}
            ],
            "fever": [
                {"condition": "Common Cold", "severity": "low", "flags": []},
                {"condition": "Flu", "severity": "medium", "flags": []},
                {"condition": "COVID-19", "severity": "medium", "flags": ["isolate", "test"]},
                {"condition": "Infection", "severity": "medium", "flags": []},
                {"condition": "Sepsis", "severity": "high", "flags": ["urgent", "emergency"]}
            ],
            "shortness_of_breath": [
                {"condition": "Asthma", "severity": "medium", "flags": []},
                {"condition": "Anxiety", "severity": "low", "flags": []},
                {"condition": "COPD", "severity": "medium", "flags": ["chronic"]},
                {"condition": "Heart Failure", "severity": "high", "flags": ["urgent"]},
                {"condition": "Pulmonary Embolism", "severity": "high", "flags": ["urgent", "emergency"]}
            ],
            "abdominal_pain": [
                {"condition": "Indigestion", "severity": "low", "flags": []},
                {"condition": "Gas", "severity": "low", "flags": []},
                {"condition": "Appendicitis", "severity": "high", "flags": ["urgent", "right_side"]},
                {"condition": "Gallstones", "severity": "medium", "flags": ["right_upper"]},
                {"condition": "Ulcer", "severity": "medium", "flags": []}
            ]
        }
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Assess patient symptoms and save the assessment.
        
        Args:
            args: Dictionary with keys:
                - patient_id: ID of the patient
                - symptoms: List of symptom descriptions
                - duration: How long symptoms have been present
                - severity: Patient-reported severity (1-10)
                - action: "assess" or "record" (default: both)
            context: Conversation context
            
        Returns:
            Dictionary with symptom assessment and recommendations
        """
        patient_id = args.get("patient_id")
        symptoms = args.get("symptoms", [])
        duration = args.get("duration", "unknown")
        severity = args.get("severity", 0)
        action = args.get("action", "both")
        
        if not patient_id:
            return {"error": "No patient ID provided"}
            
        if not symptoms:
            return {"error": "No symptoms provided for assessment"}
            
        # Normalize symptoms to known categories
        normalized_symptoms = self._normalize_symptoms(symptoms)
        
        # Create the assessment
        assessment = {
            "patient_id": patient_id,
            "symptoms": symptoms,
            "normalized_symptoms": normalized_symptoms,
            "duration": duration,
            "reported_severity": severity,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Generate the medical assessment
        possible_conditions = []
        emergency_flags = []
        max_severity = "low"
        
        for symptom in normalized_symptoms:
            if symptom in self.symptom_mapping:
                for condition in self.symptom_mapping[symptom]:
                    if condition not in possible_conditions:
                        possible_conditions.append(condition)
                    
                    # Check for emergency flags
                    if "urgent" in condition["flags"] or "emergency" in condition["flags"]:
                        emergency_flags.append(f"{condition['condition']} - {symptom}")
                    
                    # Track highest severity
                    if condition["severity"] == "high" and max_severity != "high":
                        max_severity = "high"
                    elif condition["severity"] == "medium" and max_severity == "low":
                        max_severity = "medium"
        
        # Sort conditions by severity
        possible_conditions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3))
        
        # Determine if immediate care is needed
        needs_immediate_care = max_severity == "high" or len(emergency_flags) > 0
        
        # Add assessment results
        assessment["possible_conditions"] = possible_conditions
        assessment["max_severity"] = max_severity
        assessment["emergency_flags"] = emergency_flags
        assessment["needs_immediate_care"] = needs_immediate_care
        
        # Generate recommendations
        recommendations = []
        if needs_immediate_care:
            recommendations.append("Seek immediate medical attention")
        elif max_severity == "medium":
            recommendations.append("Schedule appointment with healthcare provider soon")
        else:
            recommendations.append("Monitor symptoms")
            recommendations.append("Use over-the-counter remedies as appropriate")
        
        assessment["recommendations"] = recommendations
        
        # Record assessment if requested
        if action in ["record", "both"]:
            assessment_file = os.path.join(
                self.data_dir, 
                f"{patient_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(assessment_file, 'w') as f:
                json.dump(assessment, f, indent=2)
        
        return assessment
    
    def _normalize_symptoms(self, symptoms: List[str]) -> List[str]:
        """Map reported symptoms to standardized symptom categories."""
        normalized = []
        
        # Very basic symptom mapping - in production this would use NLP and medical ontologies
        mapping = {
            "headache": ["headache", "head pain", "head ache", "migraine"],
            "chest_pain": ["chest pain", "chest discomfort", "chest tightness", "heart pain"],
            "fever": ["fever", "high temperature", "feeling hot", "chills and fever"],
            "shortness_of_breath": ["shortness of breath", "can't breathe", "hard to breathe", "breathing difficulty"],
            "abdominal_pain": ["abdominal pain", "stomach pain", "belly pain", "stomach ache"]
        }
        
        for symptom in symptoms:
            symptom = symptom.lower()
            for category, variants in mapping.items():
                for variant in variants:
                    if variant in symptom:
                        if category not in normalized:
                            normalized.append(category)
        
        return normalized
    
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
                        "symptoms": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of symptoms the patient is experiencing"
                        },
                        "duration": {
                            "type": "string",
                            "description": "How long the patient has been experiencing the symptoms"
                        },
                        "severity": {
                            "type": "number",
                            "description": "Patient-reported severity from 1-10"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["assess", "record", "both"],
                            "description": "Whether to assess symptoms, record them, or both"
                        }
                    },
                    "required": ["patient_id", "symptoms"]
                }
            }
        }
