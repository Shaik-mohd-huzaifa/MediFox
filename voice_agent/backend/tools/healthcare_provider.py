from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

from .base_tool import BaseTool


class HealthcareProviderLookupTool(BaseTool):
    """Tool for finding healthcare providers and specialists."""
    
    def __init__(self):
        super().__init__(
            name="find_healthcare_providers",
            description="Find healthcare providers by specialty, location, or insurance acceptance"
        )
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "providers")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load or initialize provider database
        self.providers_file = os.path.join(self.data_dir, "providers_database.json")
        if not os.path.exists(self.providers_file):
            # Initialize with sample data
            self._initialize_sample_providers()
        
        with open(self.providers_file, 'r') as f:
            self.providers_db = json.load(f)
    
    def _initialize_sample_providers(self):
        """Initialize a sample provider database."""
        sample_providers = {
            "providers": [
                {
                    "id": "prov_001",
                    "name": "Dr. Jane Smith",
                    "specialties": ["Family Medicine", "Primary Care"],
                    "location": {
                        "address": "123 Health Street",
                        "city": "Medville",
                        "state": "CA",
                        "zip": "90210"
                    },
                    "insurance_accepted": ["BlueCross", "Medicare", "Aetna", "UnitedHealth"],
                    "languages": ["English", "Spanish"],
                    "accepting_patients": True
                },
                {
                    "id": "prov_002",
                    "name": "Dr. Robert Johnson",
                    "specialties": ["Cardiology", "Internal Medicine"],
                    "location": {
                        "address": "456 Heart Avenue",
                        "city": "Medville",
                        "state": "CA",
                        "zip": "90210"
                    },
                    "insurance_accepted": ["BlueCross", "Medicare", "UnitedHealth"],
                    "languages": ["English"],
                    "accepting_patients": True
                },
                {
                    "id": "prov_003",
                    "name": "Dr. Sarah Lee",
                    "specialties": ["Dermatology"],
                    "location": {
                        "address": "789 Skin Road",
                        "city": "Medville",
                        "state": "CA",
                        "zip": "90211"
                    },
                    "insurance_accepted": ["BlueCross", "Medicare", "Cigna"],
                    "languages": ["English", "Mandarin"],
                    "accepting_patients": True
                },
                {
                    "id": "prov_004",
                    "name": "Dr. Michael Wilson",
                    "specialties": ["Neurology"],
                    "location": {
                        "address": "101 Brain Lane",
                        "city": "Medville",
                        "state": "CA",
                        "zip": "90212"
                    },
                    "insurance_accepted": ["BlueCross", "Aetna", "UnitedHealth"],
                    "languages": ["English", "French"],
                    "accepting_patients": False
                },
                {
                    "id": "prov_005",
                    "name": "Dr. Emily Chen",
                    "specialties": ["Pediatrics"],
                    "location": {
                        "address": "202 Child Drive",
                        "city": "Medville",
                        "state": "CA",
                        "zip": "90210"
                    },
                    "insurance_accepted": ["BlueCross", "Medicare", "Medicaid", "UnitedHealth"],
                    "languages": ["English", "Mandarin", "Cantonese"],
                    "accepting_patients": True
                }
            ]
        }
        
        with open(self.providers_file, 'w') as f:
            json.dump(sample_providers, f, indent=2)
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Find healthcare providers based on different criteria.
        
        Args:
            args: Dictionary with keys:
                - specialty: Optional specialty to filter by
                - location: Optional location to filter by (city, state, or zip)
                - insurance: Optional insurance to filter by
                - languages: Optional languages to filter by
                - accepting_patients: Optional flag to only show providers accepting new patients
                - provider_id: Optional specific provider ID to fetch details for
            context: Conversation context
            
        Returns:
            Dictionary with matching providers
        """
        # Get specific provider details
        if "provider_id" in args:
            provider_id = args["provider_id"]
            for provider in self.providers_db["providers"]:
                if provider["id"] == provider_id:
                    return {
                        "found": True,
                        "provider": provider
                    }
            return {
                "found": False,
                "message": f"Provider with ID {provider_id} not found"
            }
        
        # Filter providers based on criteria
        filtered_providers = self.providers_db["providers"]
        
        # Filter by specialty
        if "specialty" in args and args["specialty"]:
            specialty = args["specialty"].lower()
            filtered_providers = [
                p for p in filtered_providers 
                if any(s.lower() == specialty or specialty in s.lower() for s in p["specialties"])
            ]
        
        # Filter by location
        if "location" in args and args["location"]:
            location = args["location"].lower()
            filtered_providers = [
                p for p in filtered_providers
                if (location in p["location"]["city"].lower() or 
                    location in p["location"]["state"].lower() or 
                    location in p["location"]["zip"])
            ]
        
        # Filter by insurance
        if "insurance" in args and args["insurance"]:
            insurance = args["insurance"].lower()
            filtered_providers = [
                p for p in filtered_providers
                if any(ins.lower() == insurance or insurance in ins.lower() for ins in p["insurance_accepted"])
            ]
        
        # Filter by languages
        if "languages" in args and args["languages"]:
            req_languages = [lang.lower() for lang in args["languages"]]
            filtered_providers = [
                p for p in filtered_providers
                if any(lang.lower() in req_languages for lang in p["languages"])
            ]
        
        # Filter by accepting patients
        if "accepting_patients" in args and args["accepting_patients"]:
            filtered_providers = [p for p in filtered_providers if p["accepting_patients"]]
        
        return {
            "found": len(filtered_providers) > 0,
            "providers": filtered_providers,
            "count": len(filtered_providers)
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
                        "specialty": {
                            "type": "string",
                            "description": "Medical specialty to filter providers by (e.g., 'cardiology', 'dermatology')"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location to filter providers by (city, state, or zip code)"
                        },
                        "insurance": {
                            "type": "string",
                            "description": "Insurance provider to filter by (e.g., 'Medicare', 'BlueCross')"
                        },
                        "languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Languages spoken by the provider"
                        },
                        "accepting_patients": {
                            "type": "boolean",
                            "description": "Whether to only show providers accepting new patients"
                        },
                        "provider_id": {
                            "type": "string",
                            "description": "Specific provider ID to get detailed information for"
                        }
                    }
                }
            }
        }
