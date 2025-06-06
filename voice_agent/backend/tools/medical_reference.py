from typing import Dict, Any, Optional, List
import json
import os

from .base_tool import BaseTool


class MedicalReferenceDBTool(BaseTool):
    """Tool for accessing medical reference information."""
    
    def __init__(self):
        super().__init__(
            name="access_medical_reference",
            description="Access medical condition information, treatment guidelines, and drug information"
        )
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reference")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize the medical reference database
        self.references_file = os.path.join(self.data_dir, "medical_references.json")
        if not os.path.exists(self.references_file):
            self._initialize_reference_database()
            
        with open(self.references_file, 'r') as f:
            self.reference_db = json.load(f)
    
    def _initialize_reference_database(self):
        """Initialize a sample medical reference database."""
        medical_references = {
            "conditions": {
                "hypertension": {
                    "name": "Hypertension",
                    "description": "High blood pressure is a common condition in which the long-term force of the blood against your artery walls is high enough that it may eventually cause health problems, such as heart disease.",
                    "symptoms": ["Headache", "Shortness of breath", "Nosebleeds", "Rarely asymptomatic"],
                    "treatments": [
                        "Lifestyle modifications (reduced salt intake, exercise, weight management)",
                        "Medication including ACE inhibitors, ARBs, calcium channel blockers, diuretics"
                    ],
                    "prevention": [
                        "Regular exercise",
                        "Healthy diet low in sodium",
                        "Maintain healthy weight",
                        "Limit alcohol consumption",
                        "Avoid smoking"
                    ],
                    "complications": [
                        "Heart attack or stroke",
                        "Heart failure",
                        "Aneurysm",
                        "Weakened and narrowed blood vessels in kidneys",
                        "Vision loss"
                    ]
                },
                "type2_diabetes": {
                    "name": "Type 2 Diabetes",
                    "description": "A chronic condition that affects the way the body processes blood sugar (glucose).",
                    "symptoms": [
                        "Increased thirst",
                        "Frequent urination",
                        "Increased hunger",
                        "Unintended weight loss",
                        "Fatigue",
                        "Blurred vision",
                        "Slow-healing sores"
                    ],
                    "treatments": [
                        "Lifestyle changes including diet and exercise",
                        "Monitoring blood sugar",
                        "Medications like metformin",
                        "Insulin therapy in some cases"
                    ],
                    "prevention": [
                        "Weight loss if overweight",
                        "Regular physical activity",
                        "Eating healthy foods",
                        "Avoiding sedentary lifestyle"
                    ],
                    "complications": [
                        "Heart and blood vessel disease",
                        "Nerve damage (neuropathy)",
                        "Kidney damage",
                        "Eye damage",
                        "Foot damage",
                        "Skin conditions",
                        "Alzheimer's disease"
                    ]
                },
                "asthma": {
                    "name": "Asthma",
                    "description": "A condition in which your airways narrow and swell and may produce extra mucus, making breathing difficult.",
                    "symptoms": [
                        "Shortness of breath",
                        "Chest tightness or pain",
                        "Wheezing when exhaling",
                        "Trouble sleeping caused by shortness of breath",
                        "Coughing or wheezing attacks worsened by respiratory virus"
                    ],
                    "treatments": [
                        "Quick-relief medications like short-acting beta agonists",
                        "Long-term control medications like inhaled corticosteroids",
                        "Biologics for severe cases",
                        "Bronchial thermoplasty in some cases"
                    ],
                    "prevention": [
                        "Identify and avoid asthma triggers",
                        "Take prescribed medications",
                        "Monitor breathing",
                        "Identify and treat attacks early",
                        "Get vaccinated for pneumonia and influenza"
                    ],
                    "complications": [
                        "Signs and symptoms that interfere with sleep, work or recreational activities",
                        "Permanent narrowing of the bronchial tubes (airway remodeling)",
                        "Emergency room visits and hospitalizations",
                        "Side effects from long-term use of medications"
                    ]
                }
            },
            "medications": {
                "metformin": {
                    "name": "Metformin",
                    "brand_names": ["Glucophage", "Glumetza", "Fortamet"],
                    "drug_class": "Biguanide",
                    "description": "First-line medication for the treatment of type 2 diabetes, particularly in people who are overweight.",
                    "usage": "Used to control high blood sugar in type 2 diabetes.",
                    "dosage": "Initial: 500mg twice daily with meals; can be increased gradually.",
                    "side_effects": [
                        "Nausea",
                        "Vomiting",
                        "Diarrhea",
                        "Gas",
                        "Weakness",
                        "Indigestion",
                        "Abdominal discomfort",
                        "Lactic acidosis (rare but serious)"
                    ],
                    "contraindications": [
                        "Kidney disease",
                        "Liver disease",
                        "Heart failure",
                        "Diabetic ketoacidosis"
                    ]
                },
                "lisinopril": {
                    "name": "Lisinopril",
                    "brand_names": ["Prinivil", "Zestril"],
                    "drug_class": "ACE inhibitor",
                    "description": "Medication used to treat high blood pressure and heart failure.",
                    "usage": "Treatment of hypertension, congestive heart failure, and after heart attacks.",
                    "dosage": "Initial: 10mg once daily; maintenance: 20-40mg once daily.",
                    "side_effects": [
                        "Dry cough",
                        "Dizziness",
                        "Headache",
                        "Fatigue",
                        "Nausea",
                        "Elevated potassium levels",
                        "Angioedema (rare but serious)"
                    ],
                    "contraindications": [
                        "Pregnancy (especially 2nd and 3rd trimesters)",
                        "History of angioedema",
                        "Bilateral renal artery stenosis"
                    ]
                },
                "atorvastatin": {
                    "name": "Atorvastatin",
                    "brand_names": ["Lipitor"],
                    "drug_class": "Statin",
                    "description": "Medication used to prevent cardiovascular disease and treat high cholesterol.",
                    "usage": "Treat high cholesterol and reduce risk of heart attack and stroke.",
                    "dosage": "Initial: 10-20mg once daily; range: 10-80mg once daily.",
                    "side_effects": [
                        "Muscle pain and damage",
                        "Liver function abnormalities",
                        "Digestive problems",
                        "Increased blood sugar",
                        "Neurological side effects"
                    ],
                    "contraindications": [
                        "Active liver disease",
                        "Pregnancy",
                        "Breastfeeding",
                        "Allergic reaction to statins"
                    ]
                }
            },
            "first_aid": {
                "heart_attack": {
                    "name": "Heart Attack First Aid",
                    "steps": [
                        "Call emergency services (911) immediately",
                        "Chew and swallow an aspirin if not allergic",
                        "Have the person rest in a comfortable position",
                        "Loosen tight clothing",
                        "Be prepared to perform CPR if the person becomes unconscious",
                        "If an automated external defibrillator (AED) is available and the person is unconscious, use it according to instructions"
                    ]
                },
                "stroke": {
                    "name": "Stroke First Aid",
                    "steps": [
                        "Remember FAST: Face drooping, Arm weakness, Speech difficulty, Time to call 911",
                        "Note when symptoms began",
                        "Don't give medication, food, or drinks",
                        "Have the person lie down with head slightly elevated",
                        "If unconscious, place in recovery position"
                    ]
                },
                "choking": {
                    "name": "Choking First Aid",
                    "steps": [
                        "Encourage the person to cough",
                        "If they can't breathe, speak, or cough, perform abdominal thrusts (Heimlich maneuver)",
                        "Stand behind the person with your arms around their waist",
                        "Make a fist with one hand and place it just above the navel",
                        "Grab your fist with the other hand and press inward and upward with quick thrusts",
                        "Repeat until the object is expelled or the person becomes unconscious",
                        "If unconscious, begin CPR"
                    ]
                }
            },
            "preventive_care": {
                "adult_screenings": {
                    "name": "Recommended Adult Health Screenings",
                    "screenings": [
                        {"name": "Blood pressure", "frequency": "Every year for adults 18 and older"},
                        {"name": "Cholesterol", "frequency": "Every 4-6 years for adults 20 and older"},
                        {"name": "Diabetes", "frequency": "Every 3 years for adults 45 and older or younger with risk factors"},
                        {"name": "Colorectal cancer", "frequency": "Starting at age 45, various testing options available"},
                        {"name": "Mammogram", "frequency": "Every 1-2 years for women age 40 and older"},
                        {"name": "Pap test", "frequency": "Every 3 years for women ages 21-65"},
                        {"name": "Bone density", "frequency": "At age 65 for women and younger for those with risk factors"}
                    ]
                },
                "vaccinations": {
                    "name": "Recommended Adult Vaccinations",
                    "vaccinations": [
                        {"name": "Influenza (flu)", "frequency": "Annually"},
                        {"name": "Tetanus, diphtheria, pertussis (Tdap)", "frequency": "Once, then Td booster every 10 years"},
                        {"name": "Shingles", "frequency": "Two doses for adults 50 and older"},
                        {"name": "Pneumococcal", "frequency": "One or more doses for adults 65 and older or with certain conditions"},
                        {"name": "COVID-19", "frequency": "According to current public health guidelines"}
                    ]
                }
            }
        }
        
        with open(self.references_file, 'w') as f:
            json.dump(medical_references, f, indent=2)
    
    async def run(self, args: Dict[str, Any], context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Access medical reference information.
        
        Args:
            args: Dictionary with keys:
                - category: "conditions", "medications", "first_aid", or "preventive_care"
                - query: Specific item to look up within category
                - info_type: Optional specific information type to retrieve
            context: Conversation context
            
        Returns:
            Dictionary with medical reference information
        """
        category = args.get("category")
        query = args.get("query")
        info_type = args.get("info_type")
        
        if not category:
            # Return available categories
            return {
                "available_categories": list(self.reference_db.keys()),
                "message": "Please specify a category to get medical reference information"
            }
        
        if category not in self.reference_db:
            return {
                "error": f"Category '{category}' not found",
                "available_categories": list(self.reference_db.keys())
            }
        
        if not query:
            # Return items in the category
            return {
                "category": category,
                "available_items": list(self.reference_db[category].keys())
            }
        
        # Normalize query
        query_normalized = query.lower().replace(" ", "_")
        
        if query_normalized not in self.reference_db[category]:
            close_matches = [item for item in self.reference_db[category].keys() 
                             if query_normalized in item or item in query_normalized]
            
            return {
                "found": False,
                "message": f"Could not find '{query}' in {category}",
                "suggestions": close_matches if close_matches else [],
                "available_items": list(self.reference_db[category].keys())
            }
        
        # Get the requested information
        info = self.reference_db[category][query_normalized]
        
        # If specific info type is requested
        if info_type and info_type in info:
            return {
                "found": True,
                "category": category,
                "query": query,
                "info_type": info_type,
                "result": info[info_type]
            }
        
        # Otherwise return all info
        return {
            "found": True,
            "category": category,
            "query": query,
            "result": info
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
                        "category": {
                            "type": "string",
                            "enum": ["conditions", "medications", "first_aid", "preventive_care"],
                            "description": "Category of medical reference information to access"
                        },
                        "query": {
                            "type": "string",
                            "description": "Specific item to look up within the category (e.g., a specific condition, medication, etc.)"
                        },
                        "info_type": {
                            "type": "string",
                            "description": "Optional specific type of information to retrieve (e.g., 'symptoms', 'treatments', 'side_effects')"
                        }
                    }
                }
            }
        }
