"""
Eka Care API Client for MediFox Healthcare Agent
Handles authentication and API interactions with Eka Care
"""
import os
import json
import time
from typing import Dict, Any, Optional
import requests
from pydantic import BaseModel


class EkaCredentials(BaseModel):
    """Credentials for Eka Care API authentication"""
    client_id: str
    client_secret: str
    username: Optional[str] = None
    password: Optional[str] = None


class EkaAuthToken(BaseModel):
    """Authentication token response from Eka Care"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    expires_at: float = None  # Unix timestamp when token expires


class EkaCareClient:
    """
    Client to handle interactions with the Eka Care Developer Suite APIs
    Handles authentication, token refresh, and API requests
    """
    
    BASE_URL = "https://dev.eka.care/api/v1"  # Update with actual base URL if different
    
    def __init__(self, credentials: Optional[EkaCredentials] = None):
        """Initialize with optional credentials, otherwise load from environment"""
        if credentials:
            self.credentials = credentials
        else:
            self.credentials = self._load_credentials_from_env()
            
        self.auth_token: Optional[EkaAuthToken] = None
        self.token_file = os.path.join(os.path.dirname(__file__), "eka_token_cache.json")
        self._load_cached_token()
    
    def _load_credentials_from_env(self) -> EkaCredentials:
        """Load Eka Care credentials from environment variables"""
        return EkaCredentials(
            client_id=os.environ.get("EKA_CLIENT_ID"),
            client_secret=os.environ.get("EKA_CLIENT_SECRET"),
            username=os.environ.get("EKA_USERNAME"),
            password=os.environ.get("EKA_PASSWORD")
        )
    
    def _load_cached_token(self) -> None:
        """Try to load cached token if it exists"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                    self.auth_token = EkaAuthToken(**token_data)
                    
                    # Check if token is still valid (with 5-minute buffer)
                    if self.auth_token.expires_at and time.time() >= (self.auth_token.expires_at - 300):
                        print("Cached token expired, will need to refresh")
                        if self.refresh_token():
                            print("Token refreshed successfully")
                        else:
                            print("Token refresh failed, will need to login")
                            self.auth_token = None
        except Exception as e:
            print(f"Error loading cached token: {e}")
            self.auth_token = None
    
    def _save_token_cache(self) -> None:
        """Save current token to cache file"""
        if self.auth_token:
            try:
                with open(self.token_file, "w") as f:
                    json.dump(self.auth_token.dict(), f)
            except Exception as e:
                print(f"Error saving token cache: {e}")
    
    async def ensure_authenticated(self) -> bool:
        """Ensure we have a valid authentication token"""
        if not self.auth_token:
            return await self.login()
            
        # Check if token is expired (with 5-min buffer)
        if self.auth_token.expires_at and time.time() >= (self.auth_token.expires_at - 300):
            return await self.refresh_token()
            
        return True
    
    async def login(self) -> bool:
        """
        Authenticate with Eka Care and get access token
        https://developer.eka.care/api-reference/authorization/client-login
        
        If username and password are provided, uses those for authentication.
        Otherwise, falls back to client credentials flow using only client_id and client_secret.
        """
        try:
            url = f"{self.BASE_URL}/auth/login"
            payload = {
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
            }
            
            # Add username and password if available
            if self.credentials.username and self.credentials.password:
                payload["username"] = self.credentials.username
                payload["password"] = self.credentials.password
                print("Using username/password authentication")
            else:
                print("Using client credentials flow (no username/password)")
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            data["expires_at"] = time.time() + data["expires_in"]
            self.auth_token = EkaAuthToken(**data)
            self._save_token_cache()
            
            return True
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    async def refresh_token(self) -> bool:
        """
        Refresh the authentication token
        https://developer.eka.care/api-reference/authorization/refresh-token
        """
        if not self.auth_token or not self.auth_token.refresh_token:
            print("No refresh token available, need to login")
            return await self.login()
            
        try:
            url = f"{self.BASE_URL}/auth/refresh-token"
            payload = {
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "refresh_token": self.auth_token.refresh_token,
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            data["expires_at"] = time.time() + data["expires_in"]
            self.auth_token = EkaAuthToken(**data)
            self._save_token_cache()
            
            return True
        except Exception as e:
            print(f"Token refresh error: {e}")
            # If refresh fails, try logging in again
            return await self.login()

    async def api_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """
        Make an authenticated request to the Eka Care API
        """
        if not await self.ensure_authenticated():
            raise Exception("Authentication failed")
            
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.auth_token.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method.lower() == "get":
                response = requests.get(url, params=params, headers=headers)
            elif method.lower() == "post":
                response = requests.post(url, json=data, headers=headers)
            elif method.lower() == "put":
                response = requests.put(url, json=data, headers=headers)
            elif method.lower() == "delete":
                response = requests.delete(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Try to refresh token and retry once
                if await self.refresh_token():
                    headers["Authorization"] = f"Bearer {self.auth_token.access_token}"
                    if method.lower() == "get":
                        response = requests.get(url, params=params, headers=headers)
                    elif method.lower() == "post":
                        response = requests.post(url, json=data, headers=headers)
                    elif method.lower() == "put":
                        response = requests.put(url, json=data, headers=headers)
                    elif method.lower() == "delete":
                        response = requests.delete(url, json=data, headers=headers)
                    
                    response.raise_for_status()
                    return response.json()
                    
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                error_data = {"error": str(e)}
                
            raise Exception(f"API request failed: {error_data}")
            
        except Exception as e:
            raise Exception(f"API request failed: {str(e)}")
    
    # Patient-related API methods
    
    async def add_patient(self, patient_data: Dict) -> Dict:
        """
        Add a new patient to the directory
        https://developer.eka.care/api-reference/doc-tool/patient-registration-api/add-patient-to-directory
        """
        return await self.api_request("post", "patients", data=patient_data)
    
    async def search_patient_by_mobile(self, mobile_number: str) -> Dict:
        """
        Search for patient by mobile number
        https://developer.eka.care/api-reference/doc-tool/patient-registration-api/search-patient-by-mobile
        """
        return await self.api_request("get", "patients/search", params={"mobile": mobile_number})
    
    async def get_patient_by_id(self, patient_id: str) -> Dict:
        """
        Get patient details by ID
        https://developer.eka.care/api-reference/doc-tool/patient-registration-api/get-patient-details-by-id
        """
        return await self.api_request("get", f"patients/{patient_id}")
    
    async def update_patient(self, patient_id: str, patient_data: Dict) -> Dict:
        """
        Update an existing patient's information
        """
        return await self.api_request("put", f"patients/{patient_id}", data=patient_data)
    
    # Appointment-related API methods
    
    async def get_appointment_slots(self, doctor_id: str, date: str) -> Dict:
        """
        Get available appointment slots for a doctor on a specific date
        """
        params = {
            "doctor_id": doctor_id,
            "date": date
        }
        return await self.api_request("get", "appointments/slots", params=params)
    
    async def book_appointment(self, appointment_data: Dict) -> Dict:
        """
        Book an appointment slot
        https://developer.eka.care/api-reference/doc-tool/appointment-api/book-appointment-slot
        """
        return await self.api_request("post", "appointments", data=appointment_data)
        
    async def reschedule_appointment(self, reschedule_data: Dict) -> Dict:
        """
        Reschedule an existing appointment
        
        Args:
            reschedule_data: Dictionary with the appointment_id and new details
                (slot_id or doctor_id + appointment_date + appointment_time)
        """
        appointment_id = reschedule_data.pop("appointment_id", None)
        if not appointment_id:
            raise ValueError("appointment_id is required for rescheduling")
            
        return await self.api_request("put", f"appointments/{appointment_id}", data=reschedule_data)
    
    async def get_appointment_details(self, appointment_id: str) -> Dict:
        """
        Get appointment details
        https://developer.eka.care/api-reference/doc-tool/appointment-api/get-appointment-details
        """
        return await self.api_request("get", f"appointments/{appointment_id}")
    
    async def cancel_appointment(self, appointment_id: str, reason: str) -> Dict:
        """
        Cancel an appointment
        https://developer.eka.care/api-reference/doc-tool/appointment-api/cancel-appointment
        """
        return await self.api_request("delete", f"appointments/{appointment_id}", 
                                     data={"cancellation_reason": reason})
