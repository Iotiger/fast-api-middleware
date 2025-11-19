"""
API client for communicating with MakerSuite API
"""

import json
import httpx
from typing import Dict, Any, List, Optional
from app.config import (
    MAKERSUITE_API_URL, 
    MAKERSUITE_API_KEY,
    AIRMAX_API_BASE_URL,
    AIRMAX_FLIGHT_SEARCH_ENDPOINT
)


async def send_to_makersuite_api(transformed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send transformed booking data to MakerSuite API
    """
    headers = {
        "Content-Type": "application/json",
        "ApiKey": MAKERSUITE_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        print(f"API KEY: Sending request to MakerSuite API with headers: {headers}")
        print(f"REQUEST: Request payload: {json.dumps(transformed_data, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MAKERSUITE_API_URL,
                json=transformed_data,
                headers=headers,
                timeout=30.0
            )
            
            print(f"MakerSuite API Response Status: {response.status_code}")
            print(f"MakerSuite API Response: {response.text}")
            
            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}: {response.text}"}
                
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timeout"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


async def search_flights(search_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search for flights using Airmax Flight Search API
    """
    headers = {
        "Content-Type": "application/json",
        "ApiKey": MAKERSUITE_API_KEY,
        "Accept": "application/json"
    }
    
    url = f"{AIRMAX_API_BASE_URL}{AIRMAX_FLIGHT_SEARCH_ENDPOINT}"
    
    try:
        print(f"FLIGHT SEARCH: Sending request to {url}")
        print(f"FLIGHT SEARCH: Request payload: {json.dumps(search_payload, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=search_payload,
                headers=headers,
                timeout=30.0
            )
            
            print(f"FLIGHT SEARCH: Response Status: {response.status_code}")
            print(f"FLIGHT SEARCH: Response: {response.text}")
            
            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {"success": False, "error": f"API returned status {response.status_code}: {response.text}"}
                
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timeout"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

