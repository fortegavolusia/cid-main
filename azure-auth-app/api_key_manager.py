"""
API Key Management for Service-to-Service Authentication

This module manages API keys for app-to-app authentication in CIDS.
API keys are stored hashed and provide an alternative to OAuth flows
for backend service authentication.
"""
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import hashlib
import secrets
import string
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Storage path
API_KEYS_DB = Path("app_data/app_api_keys.json")

# API Key configuration
API_KEY_PREFIX = "cids_ak_"
API_KEY_LENGTH = 32  # Length of random part after prefix
HASH_ALGORITHM = "sha256"
DEFAULT_EXPIRY_DAYS = 90
MAX_EXPIRY_DAYS = 3650  # 10 years

class APIKeyTTL(Enum):
    """Standard TTL options for API keys"""
    DAYS_30 = 30
    DAYS_90 = 90
    YEAR_1 = 365
    YEARS_5 = 1825
    YEARS_10 = 3650


@dataclass
class APIKeyMetadata:
    """Metadata for an API key"""
    key_id: str
    key_hash: str
    key_prefix: str  # First 8 chars of key for identification
    name: str
    permissions: List[str]
    expires_at: str  # ISO format datetime
    created_at: str  # ISO format datetime
    created_by: str  # Email of creator
    last_rotated_at: Optional[str] = None
    rotation_scheduled_at: Optional[str] = None
    rotation_grace_end: Optional[str] = None  # When old key expires during rotation
    is_active: bool = True
    last_used_at: Optional[str] = None
    usage_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'APIKeyMetadata':
        """Create from dictionary"""
        return cls(**data)


class APIKeyManager:
    """Manages API keys for service authentication"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, APIKeyMetadata]] = {}  # app_client_id -> key_id -> metadata
        self._key_lookup: Dict[str, Tuple[str, str]] = {}  # key_prefix -> (app_client_id, key_id)
        self._load_keys()
    
    def _load_keys(self):
        """Load API keys from storage"""
        try:
            if API_KEYS_DB.exists():
                with open(API_KEYS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, keys in data.items():
                        self.api_keys[app_id] = {}
                        for key_id, key_data in keys.items():
                            key_meta = APIKeyMetadata.from_dict(key_data)
                            self.api_keys[app_id][key_id] = key_meta
                            # Build lookup table
                            self._key_lookup[key_meta.key_prefix] = (app_id, key_id)
                            
            logger.info(f"Loaded {sum(len(keys) for keys in self.api_keys.values())} API keys")
                        
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            self.api_keys = {}
            self._key_lookup = {}
    
    def _save_keys(self):
        """Save API keys to storage"""
        try:
            # Ensure directory exists
            API_KEYS_DB.parent.mkdir(exist_ok=True)
            
            # Convert to JSON-serializable format
            data = {}
            for app_id, keys in self.api_keys.items():
                data[app_id] = {
                    key_id: key_meta.to_dict() 
                    for key_id, key_meta in keys.items()
                }
            
            with open(API_KEYS_DB, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("API keys saved successfully")
                
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
    
    def generate_api_key(self) -> str:
        """Generate a new cryptographically secure API key"""
        # Generate random string
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(API_KEY_LENGTH))
        
        # Combine with prefix
        api_key = f"{API_KEY_PREFIX}{random_part}"
        
        return api_key
    
    def hash_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify an API key against stored hash"""
        return self.hash_key(api_key) == stored_hash
    
    def create_api_key(self, 
                      app_client_id: str,
                      name: str,
                      permissions: List[str],
                      created_by: str,
                      ttl_days: int = None) -> Tuple[str, APIKeyMetadata]:
        """
        Create a new API key for an application
        
        Returns:
            Tuple of (unhashed_api_key, metadata)
        """
        # Generate key
        api_key = self.generate_api_key()
        key_id = secrets.token_urlsafe(16)
        
        # Calculate expiry
        if ttl_days is None:
            ttl_days = DEFAULT_EXPIRY_DAYS
        elif ttl_days > MAX_EXPIRY_DAYS:
            ttl_days = MAX_EXPIRY_DAYS
            
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        
        # Create metadata
        metadata = APIKeyMetadata(
            key_id=key_id,
            key_hash=self.hash_key(api_key),
            key_prefix=api_key[:len(API_KEY_PREFIX) + 8],  # Store prefix + first 8 chars
            name=name,
            permissions=permissions,
            expires_at=expires_at.isoformat(),
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            is_active=True
        )
        
        # Store metadata
        if app_client_id not in self.api_keys:
            self.api_keys[app_client_id] = {}
        
        self.api_keys[app_client_id][key_id] = metadata
        self._key_lookup[metadata.key_prefix] = (app_client_id, key_id)
        
        # Save to disk
        self._save_keys()
        
        return api_key, metadata
    
    def list_api_keys(self, app_client_id: str) -> List[APIKeyMetadata]:
        """List all API keys for an application"""
        if app_client_id not in self.api_keys:
            return []
        
        return list(self.api_keys[app_client_id].values())
    
    def get_api_key(self, app_client_id: str, key_id: str) -> Optional[APIKeyMetadata]:
        """Get a specific API key metadata"""
        if app_client_id not in self.api_keys:
            return None
        
        return self.api_keys[app_client_id].get(key_id)
    
    def revoke_api_key(self, app_client_id: str, key_id: str) -> bool:
        """Revoke an API key"""
        if app_client_id not in self.api_keys:
            return False
        
        if key_id not in self.api_keys[app_client_id]:
            return False
        
        # Mark as inactive
        self.api_keys[app_client_id][key_id].is_active = False
        
        # Remove from lookup table
        key_prefix = self.api_keys[app_client_id][key_id].key_prefix
        if key_prefix in self._key_lookup:
            del self._key_lookup[key_prefix]
        
        # Save changes
        self._save_keys()
        
        return True
    
    def rotate_api_key(self, 
                      app_client_id: str, 
                      key_id: str,
                      created_by: str,
                      grace_period_hours: int = 24) -> Optional[Tuple[str, APIKeyMetadata]]:
        """
        Rotate an API key with grace period
        
        Returns:
            Tuple of (new_unhashed_api_key, new_metadata) or None if key not found
        """
        # Get existing key
        old_key = self.get_api_key(app_client_id, key_id)
        if not old_key:
            return None
        
        # Create new key with same permissions and name
        new_key, new_metadata = self.create_api_key(
            app_client_id=app_client_id,
            name=f"{old_key.name} (Rotated)",
            permissions=old_key.permissions,
            created_by=created_by,
            ttl_days=APIKeyTTL.DAYS_90.value  # Default rotation TTL
        )
        
        # Update old key with rotation info
        old_key.last_rotated_at = datetime.utcnow().isoformat()
        old_key.rotation_scheduled_at = (
            datetime.utcnow() + timedelta(hours=grace_period_hours)
        ).isoformat()
        old_key.rotation_grace_end = old_key.rotation_scheduled_at
        
        # Save changes
        self._save_keys()
        
        return new_key, new_metadata
    
    def validate_api_key(self, api_key: str) -> Optional[Tuple[str, APIKeyMetadata]]:
        """
        Validate an API key and return app_id and metadata if valid
        
        Returns:
            Tuple of (app_client_id, metadata) or None if invalid
        """
        # Extract prefix for lookup
        if not api_key.startswith(API_KEY_PREFIX):
            return None
        
        key_prefix = api_key[:len(API_KEY_PREFIX) + 8]
        
        # Look up key
        if key_prefix not in self._key_lookup:
            return None
        
        app_client_id, key_id = self._key_lookup[key_prefix]
        
        # Get metadata
        if app_client_id not in self.api_keys:
            return None
        
        if key_id not in self.api_keys[app_client_id]:
            return None
        
        metadata = self.api_keys[app_client_id][key_id]
        
        # Verify hash
        if not self.verify_key(api_key, metadata.key_hash):
            return None
        
        # Check if active
        if not metadata.is_active:
            return None
        
        # Check expiry
        if metadata.expires_at:
            expires = datetime.fromisoformat(metadata.expires_at)
            if datetime.utcnow() > expires:
                return None
        
        # Check rotation grace period
        if metadata.rotation_grace_end:
            grace_end = datetime.fromisoformat(metadata.rotation_grace_end)
            if datetime.utcnow() > grace_end:
                # Grace period expired, deactivate key
                metadata.is_active = False
                self._save_keys()
                return None
        
        # Update usage stats
        metadata.last_used_at = datetime.utcnow().isoformat()
        metadata.usage_count += 1
        self._save_keys()
        
        return app_client_id, metadata
    
    def cleanup_expired_keys(self) -> int:
        """Remove expired and inactive keys. Returns count of removed keys."""
        removed_count = 0
        
        for app_id in list(self.api_keys.keys()):
            keys_to_remove = []
            
            for key_id, metadata in self.api_keys[app_id].items():
                # Check if expired
                if metadata.expires_at:
                    expires = datetime.fromisoformat(metadata.expires_at)
                    if datetime.utcnow() > expires:
                        keys_to_remove.append(key_id)
                        continue
                
                # Check rotation grace period
                if metadata.rotation_grace_end:
                    grace_end = datetime.fromisoformat(metadata.rotation_grace_end)
                    if datetime.utcnow() > grace_end and not metadata.is_active:
                        keys_to_remove.append(key_id)
            
            # Remove expired keys
            for key_id in keys_to_remove:
                key_prefix = self.api_keys[app_id][key_id].key_prefix
                if key_prefix in self._key_lookup:
                    del self._key_lookup[key_prefix]
                del self.api_keys[app_id][key_id]
                removed_count += 1
        
        if removed_count > 0:
            self._save_keys()
            logger.info(f"Cleaned up {removed_count} expired API keys")
        
        return removed_count
    
    def get_keys_needing_rotation(self, days_before_expiry: int = 7) -> List[Tuple[str, str, APIKeyMetadata]]:
        """
        Get API keys that are approaching expiry and should be rotated
        
        Returns:
            List of (app_client_id, key_id, metadata) tuples
        """
        keys_to_rotate = []
        threshold = datetime.utcnow() + timedelta(days=days_before_expiry)
        
        for app_id, keys in self.api_keys.items():
            for key_id, metadata in keys.items():
                if not metadata.is_active:
                    continue
                
                if metadata.expires_at:
                    expires = datetime.fromisoformat(metadata.expires_at)
                    if expires <= threshold:
                        keys_to_rotate.append((app_id, key_id, metadata))
        
        return keys_to_rotate


# Global API key manager instance
api_key_manager = APIKeyManager()