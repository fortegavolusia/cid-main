"""JWT Utilities for Internal Token Management (migrated)"""
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from authlib.jose import jwt, JsonWebKey
import logging

from services.token_templates import TokenTemplateManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class JWTManager:
    def __init__(self, key_path: Optional[str] = None):
        self.key_path = key_path
        self.private_key = None
        self.public_key = None
        self.private_pem = None
        self.public_pem = None
        self.kid = "auth-service-key-1"
        self.template_manager = TokenTemplateManager()
        self._initialize_keys()

    def _initialize_keys(self):
        if self.key_path and os.path.exists(f"{self.key_path}/private_key.pem"):
            self._load_keys()
        else:
            self._generate_keys()
            if self.key_path:
                self._save_keys()

    def _generate_keys(self):
        logger.info("Generating new RSA key pair")
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        self.public_key = self.private_key.public_key()
        self.private_pem = self.private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
        self.public_pem = self.public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)

    def _load_keys(self):
        logger.info(f"Loading RSA keys from {self.key_path}")
        with open(f"{self.key_path}/private_key.pem", "rb") as f:
            self.private_pem = f.read()
            self.private_key = serialization.load_pem_private_key(self.private_pem, password=None, backend=default_backend())
        with open(f"{self.key_path}/public_key.pem", "rb") as f:
            self.public_pem = f.read()
            self.public_key = serialization.load_pem_public_key(self.public_pem, backend=default_backend())

    def _save_keys(self):
        os.makedirs(self.key_path, exist_ok=True)
        with open(f"{self.key_path}/private_key.pem", "wb") as f:
            f.write(self.private_pem)
        with open(f"{self.key_path}/public_key.pem", "wb") as f:
            f.write(self.public_pem)
        logger.info(f"RSA keys saved to {self.key_path}")

    def create_token(self, user_info: Dict, token_lifetime_minutes: int = 30, token_type: str = 'access') -> str:
        now = datetime.now(timezone.utc)
        claims = {
            'iss': 'internal-auth-service',
            'sub': user_info['sub'],
            'aud': 'internal-services',
            'iat': now,
            'nbf': now,
            'exp': now + timedelta(minutes=token_lifetime_minutes),
            'jti': os.urandom(16).hex(),
            'token_type': token_type,
        }
        if token_type == 'access':
            groups = user_info.get('groups', [])
            if groups and isinstance(groups[0], dict):
                processed_groups = [g.get('displayName', '') for g in groups]
            else:
                processed_groups = groups
            token_version = user_info.get('token_version', '2.0')
            claims.update(user_info)
            if token_version not in ['2.0', '3.0']:
                logger.warning(f"Invalid token version {token_version}, defaulting to v2.0")
                claims['token_version'] = '2.0'
            else:
                claims['token_version'] = token_version
            try:
                claims = self.template_manager.apply_template(claims, processed_groups)
            except Exception as e:
                logger.warning(f"Failed to apply token template: {e}. Using full claims.")
        elif token_type == 'refresh':
            claims.update({'token_version': '2.0', 'token_use': 'refresh'})
        elif token_type == 'service':
            token_version = user_info.get('token_version', '2.0')
            claims.update(user_info)
            claims['token_version'] = token_version
        header = {'alg': 'RS256', 'kid': self.kid}
        token = jwt.encode(header, claims, self.private_pem)
        return token.decode('utf-8') if isinstance(token, bytes) else token

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        try:
            claims = jwt.decode(token, self.public_pem)
            now = datetime.now(timezone.utc)
            exp = claims.get('exp')
            nbf = claims.get('nbf')
            if exp and datetime.fromtimestamp(exp, timezone.utc) < now:
                return False, None, "Token has expired"
            if nbf and datetime.fromtimestamp(nbf, timezone.utc) > now:
                return False, None, "Token not yet valid"
            if claims.get('iss') != 'internal-auth-service':
                return False, None, "Invalid token issuer"
            aud = claims.get('aud')
            if isinstance(aud, list):
                has_valid_audience = any(a == 'internal-services' or a.startswith('app_') for a in aud)
                if not has_valid_audience:
                    return False, None, "Invalid token audience"
            elif isinstance(aud, str):
                if aud != 'internal-services' and not aud.startswith('app_'):
                    return False, None, "Invalid token audience"
            else:
                return False, None, "Invalid token audience"
            return True, claims, None
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False, None, str(e)

    def get_public_key_jwks(self) -> Dict:
        key = JsonWebKey.import_key(self.public_pem, {'kty': 'RSA', 'use': 'sig', 'kid': self.kid, 'alg': 'RS256'})
        return {'keys': [key.as_dict()]}

    def introspect_token(self, token: str) -> Dict:
        is_valid, claims, error = self.validate_token(token)
        if not is_valid:
            return {'active': False, 'error': error}
        return {
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
            'email': claims.get('email'),
            'name': claims.get('name'),
            'groups': claims.get('groups', []),
        }

