"""
Example client showing how to validate tokens with the auth service
"""
import httpx
import asyncio
from typing import Dict, Optional, Tuple
from authlib.jose import jwt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthServiceClient:
    """Client for interacting with the centralized auth service"""
    
    def __init__(self, auth_service_url: str = "https://10.1.5.58:8000"):
        self.auth_service_url = auth_service_url
        self.public_keys = None
        self.public_keys_cache_time = None
        
    async def get_public_keys(self, force_refresh: bool = False) -> Dict:
        """
        Get public keys from auth service (with caching)
        """
        # Cache for 1 hour
        if not force_refresh and self.public_keys and self.public_keys_cache_time:
            from datetime import datetime, timedelta
            if datetime.now() - self.public_keys_cache_time < timedelta(hours=1):
                return self.public_keys
        
        async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed cert
            response = await client.get(f"{self.auth_service_url}/auth/public-key")
            response.raise_for_status()
            
            self.public_keys = response.json()
            self.public_keys_cache_time = datetime.now()
            
            return self.public_keys
    
    async def validate_token_locally(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate token locally using cached public keys
        """
        try:
            # Get public keys
            jwks = await self.get_public_keys()
            
            # Decode and validate
            claims = jwt.decode(token, jwks)
            
            # Check expiration
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            exp = claims.get('exp')
            
            if exp and datetime.fromtimestamp(exp, timezone.utc) < now:
                return False, None, "Token expired"
            
            return True, claims, None
            
        except Exception as e:
            logger.error(f"Local token validation failed: {e}")
            return False, None, str(e)
    
    async def validate_token_remote(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate token by calling the auth service
        """
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.auth_service_url}/auth/validate",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return True, data, None
                else:
                    return False, None, response.json().get('detail', 'Validation failed')
                    
        except Exception as e:
            logger.error(f"Remote token validation failed: {e}")
            return False, None, str(e)
    
    async def introspect_token(self, token: str) -> Dict:
        """
        Get detailed token information using introspection endpoint
        """
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.auth_service_url}/auth/introspect",
                    json={"token": token}
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Token introspection failed: {e}")
            return {"active": False, "error": str(e)}


# Example usage
async def main():
    # Initialize client
    client = AuthServiceClient()
    
    # Example token (you would get this from a request header)
    # token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImF1dGgtc2VydmljZS1rZXktMSJ9..."
    
    print("Auth Service Client Example")
    print("=" * 50)
    
    # Get public keys
    print("\n1. Fetching public keys...")
    keys = await client.get_public_keys()
    print(f"   Retrieved {len(keys['keys'])} public key(s)")
    
    # Example of how to validate a token (if you had one)
    # print("\n2. Validating token locally...")
    # is_valid, claims, error = await client.validate_token_locally(token)
    # if is_valid:
    #     print(f"   ✓ Token valid for user: {claims.get('name')}")
    # else:
    #     print(f"   ✗ Token invalid: {error}")
    
    print("\nTo test token validation:")
    print("1. Login via the web interface")
    print("2. Click 'Get Current Token' to get your token")
    print("3. Use that token in this client example")


if __name__ == "__main__":
    asyncio.run(main())