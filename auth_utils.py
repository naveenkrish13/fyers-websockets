import os
import json
import hashlib
from typing import Dict, Any, Tuple, Optional
import requests
from database import upsert_auth

def authenticate_broker(request_token: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Authenticate with FYERS API using request token and return access token with user details.
    
    Args:
        request_token: The authorization code received from FYERS
        
    Returns:
        Tuple of (access_token, response_data). 
        - access_token: The authentication token if successful, None otherwise
        - response_data: Full response data or error details
    """
    # Initialize response data
    response_data = {
        'status': 'error',
        'message': 'Authentication failed',
        'data': None
    }
    
    # Get environment variables
    broker_api_key = os.getenv('BROKER_API_KEY')
    broker_api_secret = os.getenv('BROKER_API_SECRET')
    
    # Validate environment variables
    if not broker_api_key or not broker_api_secret:
        error_msg = "Missing BROKER_API_KEY or BROKER_API_SECRET in environment variables"
        print(error_msg)
        response_data['message'] = error_msg
        return None, response_data
    
    if not request_token:
        error_msg = "No request token provided"
        print(error_msg)
        response_data['message'] = error_msg
        return None, response_data
    
    # FYERS's endpoint for session token exchange
    url = 'https://api-t1.fyers.in/api/v3/validate-authcode'
    
    try:
        # Generate the checksum as a SHA-256 hash of concatenated api_key and api_secret
        checksum_input = f"{broker_api_key}:{broker_api_secret}"
        app_id_hash = hashlib.sha256(checksum_input.encode('utf-8')).hexdigest()
        
        # Prepare the request payload
        payload = {
            'grant_type': 'authorization_code',
            'appIdHash': app_id_hash,
            'code': request_token
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print(f"Authenticating with FYERS API. Request: {json.dumps(payload, indent=2)}")
        
        # Make the authentication request
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        # Process the response
        response.raise_for_status()
        auth_data = response.json()
        print(f"FYERS auth API response: {json.dumps(auth_data, indent=2)}")
        
        if auth_data.get('s') == 'ok':
            access_token = auth_data.get('access_token')
            if not access_token:
                error_msg = "Authentication succeeded but no access token was returned"
                print(error_msg)
                response_data['message'] = error_msg
                return None, response_data
                
            # Prepare success response
            response_data.update({
                'status': 'success',
                'message': 'Authentication successful',
                'data': {
                    'access_token': access_token,
                    'refresh_token': auth_data.get('refresh_token'),
                    'expires_in': auth_data.get('expires_in')
                }
            })
            
            print("Successfully authenticated with FYERS API")
            return access_token, response_data
            
        else:
            # Handle API error response
            error_msg = auth_data.get('message', 'Authentication failed')
            print(f"FYERS API error: {error_msg}")
            response_data['message'] = f"API error: {error_msg}"
            return None, response_data
            
    except Exception as e:
        error_msg = f"Authentication failed: {e}"
        print(f"Authentication failed due to an unexpected error: {e}")
        response_data['message'] = error_msg
        return None, response_data

def handle_auth_success(auth_token, username, broker='fyers'):
    """Handle successful authentication by storing token in database"""
    try:
        # Get API credentials from environment
        api_key = os.getenv('BROKER_API_KEY')
        api_secret = os.getenv('BROKER_API_SECRET')
        
        # Store the auth token, API key, and API secret in database
        inserted_id = upsert_auth(
            name=username, 
            auth_token=auth_token, 
            broker=broker,
            api_key=api_key,
            api_secret=api_secret
        )
        if inserted_id is not None:
            print(f"Database Upserted record with ID: {inserted_id}")
            print(f'Auth token and API credentials stored in the Database for user: {username}')
            return True
        else:
            print(f"Failed to upsert auth token for user: {username}")
            return False
    except Exception as e:
        print(f"Error handling auth success: {e}")
        return False

def mask_api_credential(credential):
    """Mask API credentials for display purposes"""
    if not credential or len(credential) < 8:
        return "****"
    return credential[:4] + "*" * (len(credential) - 8) + credential[-4:]