"""JWKS (JSON Web Key Set) handler for CIDS"""
from typing import Dict, List, Any
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

class JWKSHandler:
    """Handles JWKS operations for the auth service"""
    
    def __init__(self, jwt_manager):
        self.jwt_manager = jwt_manager
    
    def get_jwks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate JWKS from the current RSA keys"""
        keys = []
        
        # Get the current public key
        public_key = self.jwt_manager.public_key
        public_numbers = public_key.public_numbers()
        
        # Convert to base64url encoding
        def int_to_base64url(num: int) -> str:
            # Convert integer to bytes, then base64url encode
            num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
            return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode('ascii')
        
        # Create JWK
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "kid": self.jwt_manager.kid,
            "alg": "RS256",
            "n": int_to_base64url(public_numbers.n),
            "e": int_to_base64url(public_numbers.e)
        }
        
        keys.append(jwk)
        
        # Include previous key if in rotation period
        if hasattr(self.jwt_manager, 'previous_public_key') and self.jwt_manager.previous_public_key:
            prev_public_numbers = self.jwt_manager.previous_public_key.public_numbers()
            prev_jwk = {
                "kty": "RSA",
                "use": "sig",
                "kid": "auth-service-key-previous",  # Use static previous kid
                "alg": "RS256",
                "n": int_to_base64url(prev_public_numbers.n),
                "e": int_to_base64url(prev_public_numbers.e)
            }
            keys.append(prev_jwk)
        
        return {"keys": keys}
    
    def get_metadata(self, base_url: str) -> Dict[str, Any]:
        """Generate CIDS metadata configuration"""
        return {
            "issuer": "internal-auth-service",
            "token_endpoint": f"{base_url}/oauth/token",
            "jwks_uri": f"{base_url}/.well-known/jwks.json",
            "authorization_endpoint": f"{base_url}/auth/login",
            "response_types_supported": ["code", "token"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "claims_supported": [
                "sub", "email", "name", "groups", "roles", "attrs",
                "aud", "iss", "iat", "exp", "nbf", "jti"
            ],
            "service_documentation": f"{base_url}/docs",
            "service_version": "1.0.0"
        }