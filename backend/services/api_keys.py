"""API Key Management (migrated)"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
import hashlib
import secrets
import string
from dataclasses import dataclass, asdict
from enum import Enum

from backend.utils.paths import data_path

logger = logging.getLogger(__name__)

API_KEYS_DB = data_path("app_api_keys.json")
API_KEY_PREFIX = "cids_ak_"
API_KEY_LENGTH = 32
HASH_ALGORITHM = "sha256"
DEFAULT_EXPIRY_DAYS = 90
MAX_EXPIRY_DAYS = 3650


class APIKeyTTL(Enum):
    DAYS_30 = 30
    DAYS_90 = 90
    YEAR_1 = 365
    YEARS_5 = 1825
    YEARS_10 = 3650


@dataclass
class APIKeyMetadata:
    key_id: str
    key_hash: str
    key_prefix: str
    name: str
    permissions: List[str]
    expires_at: str
    created_at: str
    created_by: str
    last_rotated_at: Optional[str] = None
    rotation_scheduled_at: Optional[str] = None
    rotation_grace_end: Optional[str] = None
    is_active: bool = True
    last_used_at: Optional[str] = None
    usage_count: int = 0
    # A2A (App-to-App) fields
    token_template_name: Optional[str] = None
    app_roles_overrides: Optional[Dict[str, List[str]]] = None
    token_ttl_minutes: Optional[int] = None
    default_audience: Optional[str] = None
    allowed_audiences: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> 'APIKeyMetadata':
        return cls(**data)


class APIKeyManager:
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, APIKeyMetadata]] = {}
        self._key_lookup: Dict[str, Tuple[str, str]] = {}
        self._load_keys()

    def _load_keys(self):
        try:
            if API_KEYS_DB.exists():
                with open(API_KEYS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, keys in data.items():
                        self.api_keys[app_id] = {}
                        for key_id, key_data in keys.items():
                            key_meta = APIKeyMetadata.from_dict(key_data)
                            self.api_keys[app_id][key_id] = key_meta
                            self._key_lookup[key_meta.key_prefix] = (app_id, key_id)
            logger.info(f"Loaded {sum(len(keys) for keys in self.api_keys.values())} API keys")
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            self.api_keys = {}
            self._key_lookup = {}

    def _save_keys(self):
        try:
            API_KEYS_DB.parent.mkdir(parents=True, exist_ok=True)
            data = {app_id: {key_id: key_meta.to_dict() for key_id, key_meta in keys.items()} for app_id, keys in self.api_keys.items()}
            with open(API_KEYS_DB, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")

    def generate_api_key(self) -> str:
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(API_KEY_LENGTH))
        return f"{API_KEY_PREFIX}{random_part}"

    def hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_key(self, api_key: str, stored_hash: str) -> bool:
        return self.hash_key(api_key) == stored_hash

    def create_api_key(self, app_client_id: str, name: str, permissions: List[str], created_by: str, ttl_days: int = None,
                      token_template_name: Optional[str] = None, app_roles_overrides: Optional[Dict[str, List[str]]] = None,
                      token_ttl_minutes: Optional[int] = None, default_audience: Optional[str] = None,
                      allowed_audiences: Optional[List[str]] = None) -> Tuple[str, APIKeyMetadata]:
        api_key = self.generate_api_key()
        key_id = secrets.token_urlsafe(16)
        ttl_days = DEFAULT_EXPIRY_DAYS if ttl_days is None else min(ttl_days, MAX_EXPIRY_DAYS)
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        metadata = APIKeyMetadata(
            key_id=key_id,
            key_hash=self.hash_key(api_key),
            key_prefix=api_key[:len(API_KEY_PREFIX) + 8],
            name=name,
            permissions=permissions,
            expires_at=expires_at.isoformat(),
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            is_active=True,
            token_template_name=token_template_name,
            app_roles_overrides=app_roles_overrides,
            token_ttl_minutes=token_ttl_minutes,
            default_audience=default_audience,
            allowed_audiences=allowed_audiences,
        )
        if app_client_id not in self.api_keys:
            self.api_keys[app_client_id] = {}
        self.api_keys[app_client_id][key_id] = metadata
        self._key_lookup[metadata.key_prefix] = (app_client_id, key_id)
        self._save_keys()
        return api_key, metadata

    def list_api_keys(self, app_client_id: str) -> List[APIKeyMetadata]:
        if app_client_id not in self.api_keys:
            return []
        return list(self.api_keys[app_client_id].values())

    def get_api_key(self, app_client_id: str, key_id: str) -> Optional[APIKeyMetadata]:
        if app_client_id not in self.api_keys:
            return None
        return self.api_keys[app_client_id].get(key_id)

    def revoke_api_key(self, app_client_id: str, key_id: str) -> bool:
        if app_client_id not in self.api_keys:
            return False
        if key_id not in self.api_keys[app_client_id]:
            return False
        self.api_keys[app_client_id][key_id].is_active = False
        key_prefix = self.api_keys[app_client_id][key_id].key_prefix
        if key_prefix in self._key_lookup:
            del self._key_lookup[key_prefix]
        self._save_keys()
        return True

    def rotate_api_key(self, app_client_id: str, key_id: str, created_by: str, grace_period_hours: int = 24) -> Optional[Tuple[str, APIKeyMetadata]]:
        old_key = self.get_api_key(app_client_id, key_id)
        if not old_key:
            return None
        new_key, new_metadata = self.create_api_key(
            app_client_id=app_client_id,
            name=f"{old_key.name} (Rotated)",
            permissions=old_key.permissions,
            created_by=created_by,
            ttl_days=APIKeyTTL.DAYS_90.value,
        )
        old_key.last_rotated_at = datetime.utcnow().isoformat()
        old_key.rotation_scheduled_at = (datetime.utcnow() + timedelta(hours=grace_period_hours)).isoformat()
        old_key.rotation_grace_end = old_key.rotation_scheduled_at
        self._save_keys()
        return new_key, new_metadata

    def validate_api_key(self, api_key: str) -> Optional[Tuple[str, APIKeyMetadata]]:
        if not api_key.startswith(API_KEY_PREFIX):
            return None
        key_prefix = api_key[:len(API_KEY_PREFIX) + 8]
        if key_prefix not in self._key_lookup:
            return None
        app_client_id, key_id = self._key_lookup[key_prefix]
        if app_client_id not in self.api_keys:
            return None
        if key_id not in self.api_keys[app_client_id]:
            return None
        metadata = self.api_keys[app_client_id][key_id]
        if not self.verify_key(api_key, metadata.key_hash):
            return None
        if not metadata.is_active:
            return None
        if metadata.expires_at:
            expires = datetime.fromisoformat(metadata.expires_at)
            if datetime.utcnow() > expires:
                return None
        if metadata.rotation_grace_end:
            grace_end = datetime.fromisoformat(metadata.rotation_grace_end)
            if datetime.utcnow() > grace_end:
                metadata.is_active = False
                self._save_keys()
                return None
        metadata.last_used_at = datetime.utcnow().isoformat()
        metadata.usage_count += 1
        self._save_keys()
        return app_client_id, metadata

    def get_keys_needing_rotation(self, days_before_expiry: int = 7):
        """Yield (app_id, key_id, metadata) for keys expiring within threshold and still active."""
        try:
            threshold = datetime.utcnow() + timedelta(days=days_before_expiry)
            for app_id, keys in self.api_keys.items():
                for key_id, metadata in keys.items():
                    if not metadata.is_active:
                        continue
                    if not metadata.expires_at:
                        continue
                    try:
                        expires = datetime.fromisoformat(metadata.expires_at)
                    except Exception:
                        continue
                    if expires <= threshold:
                        yield app_id, key_id, metadata
        except Exception as e:
            logger.error(f"Error scanning keys for rotation: {e}")
            return

    def cleanup_expired_keys(self) -> int:
        removed_count = 0
        for app_id in list(self.api_keys.keys()):
            keys_to_remove = []
            for key_id, metadata in self.api_keys[app_id].items():
                if metadata.expires_at:
                    expires = datetime.fromisoformat(metadata.expires_at)
                    if datetime.utcnow() > expires:
                        keys_to_remove.append(key_id)
                        continue
                if metadata.rotation_grace_end:
                    grace_end = datetime.fromisoformat(metadata.rotation_grace_end)
                    if datetime.utcnow() > grace_end and not metadata.is_active:
                        keys_to_remove.append(key_id)
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


api_key_manager = APIKeyManager()

