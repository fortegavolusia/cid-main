"""
JWT Utilities for Internal Token Management
"""
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from authlib.jose import jwt, JsonWebKey
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class JWTManager:
    """Manages RSA keys and JWT operations for the auth service"""
    
    def __init__(self, key_path: Optional[str] = None):
        """
        Initialize JWT Manager
        
        Args:
            key_path: Path to store/load RSA keys. If None, generates new keys in memory.
        """
        self.key_path = key_path
        self.private_key = None
        self.public_key = None
        self.private_pem = None
        self.public_pem = None
        self.kid = "auth-service-key-1"  # Key ID for rotation support
        
        self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize RSA keys - load from file or generate new ones"""
        if self.key_path and os.path.exists(f"{self.key_path}/private_key.pem"):
            self._load_keys()
        else:
            self._generate_keys()
            if self.key_path:
                self._save_keys()
    
    def _generate_keys(self):
        """Generate new RSA key pair"""
        logger.info("Generating new RSA key pair")
        
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        # Convert to PEM format
        self.private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def _load_keys(self):
        """Load existing RSA keys from files"""
        logger.info(f"Loading RSA keys from {self.key_path}")
        
        with open(f"{self.key_path}/private_key.pem", "rb") as f:
            self.private_pem = f.read()
            self.private_key = serialization.load_pem_private_key(
                self.private_pem, password=None, backend=default_backend()
            )
        
        with open(f"{self.key_path}/public_key.pem", "rb") as f:
            self.public_pem = f.read()
            self.public_key = serialization.load_pem_public_key(
                self.public_pem, backend=default_backend()
            )
    
    def _save_keys(self):
        """Save RSA keys to files"""
        os.makedirs(self.key_path, exist_ok=True)
        
        with open(f"{self.key_path}/private_key.pem", "wb") as f:
            f.write(self.private_pem)
        
        with open(f"{self.key_path}/public_key.pem", "wb") as f:
            f.write(self.public_pem)
        
        logger.info(f"RSA keys saved to {self.key_path}")
    
    def create_token(self, user_info: Dict, token_lifetime_minutes: int = 30, token_type: str = 'access') -> str:
        """
        Create a signed JWT token with user information
        
        Args:
            user_info: Dictionary containing user information
            token_lifetime_minutes: Token lifetime in minutes
            token_type: Type of token ('access' or 'refresh')
            
        Returns:
            Signed JWT token as string
        """
        now = datetime.now(timezone.utc)
        
        # Define standard claims
        claims = {
            'iss': 'internal-auth-service',
            'sub': user_info['sub'],
            'aud': 'internal-services',
            'iat': now,
            'nbf': now,  # Not valid before
            'exp': now + timedelta(minutes=token_lifetime_minutes),
            'jti': os.urandom(16).hex(),  # Unique token ID
            'token_type': token_type,
        }
        
        # Add custom claims based on token type
        if token_type == 'access':
            # Handle groups - they might be dicts or already processed strings
            groups = user_info.get('groups', [])
            if groups and isinstance(groups[0], dict):
                # Extract displayName from dict format
                processed_groups = [g.get('displayName', '') for g in groups]
            else:
                # Already strings or other format
                processed_groups = groups
                
            # For v2.0 tokens, most claims are already set
            if user_info.get('token_version') == '2.0':
                # Just update with any missing standard claims
                claims.update(user_info)
            else:
                # Legacy v1.0 token format
                claims.update({
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'groups': processed_groups,
                    'token_version': '1.0',
                })
        elif token_type == 'refresh':
            # Refresh tokens have minimal claims
            claims.update({
                'token_version': '1.0',
                'token_use': 'refresh',
            })
        
        # Sign token
        header = {'alg': 'RS256', 'kid': self.kid}
        token = jwt.encode(header, claims, self.private_pem)
        
        return token.decode('utf-8') if isinstance(token, bytes) else token
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate a JWT token
        
        Args:
            token: JWT token to validate
            
        Returns:
            Tuple of (is_valid, claims, error_message)
        """
        logger.debug(f"Validating token: {token[:20] + '...' if len(token) > 20 else token}")
        try:
            # Decode and validate
            claims = jwt.decode(token, self.public_pem)
            logger.debug(f"Token decoded successfully. Claims: {claims}")
            
            # Additional validation
            now = datetime.now(timezone.utc)
            exp = claims.get('exp')
            nbf = claims.get('nbf')
            
            if exp and datetime.fromtimestamp(exp, timezone.utc) < now:
                return False, None, "Token has expired"
            
            if nbf and datetime.fromtimestamp(nbf, timezone.utc) > now:
                return False, None, "Token not yet valid"
            
            if claims.get('iss') != 'internal-auth-service':
                return False, None, "Invalid token issuer"
            
            # Handle audience as string or list
            aud = claims.get('aud')
            if isinstance(aud, list):
                if 'internal-services' not in aud:
                    return False, None, "Invalid token audience"
            elif aud != 'internal-services':
                return False, None, "Invalid token audience"
            
            return True, claims, None
            
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            logger.error(f"Token validation error type: {type(e).__name__}")
            logger.error(f"Token being validated: {token[:50]}...")
            return False, None, str(e)
    
    def get_public_key_jwks(self) -> Dict:
        """
        Get public key in JWKS format
        
        Returns:
            JWKS dictionary containing the public key
        """
        key = JsonWebKey.import_key(
            self.public_pem,
            {'kty': 'RSA', 'use': 'sig', 'kid': self.kid, 'alg': 'RS256'}
        )
        
        return {
            'keys': [key.as_dict()]
        }
    
    def introspect_token(self, token: str) -> Dict:
        """
        Introspect a token (RFC 7662 compatible response)
        
        Args:
            token: JWT token to introspect
            
        Returns:
            Token introspection response
        """
        is_valid, claims, error = self.validate_token(token)
        
        if not is_valid:
            return {
                'active': False,
                'error': error
            }
        
        # Build introspection response
        response = {
            'active': True,
            'sub': claims.get('sub'),
            'aud': claims.get('aud'),
            'iss': claims.get('iss'),
            'exp': claims.get('exp'),
            'iat': claims.get('iat'),
            'nbf': claims.get('nbf'),
            'jti': claims.get('jti'),
            'token_type': 'Bearer',
            'scope': 'profile email groups',
            # Custom claims
            'email': claims.get('email'),
            'name': claims.get('name'),
            'groups': claims.get('groups', []),
        }
        
        return response