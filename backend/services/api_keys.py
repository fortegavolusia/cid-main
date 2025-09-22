"""API Key Management (migrated)"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
# import json  # No longer needed - using database now
import logging
import hashlib
import secrets
import string
from dataclasses import dataclass, asdict
from enum import Enum

# from utils.paths import data_path  # No longer needed - using database now

logger = logging.getLogger(__name__)

# API_KEYS_DB = data_path("app_api_keys.json")  # No longer needed - using database now
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
        """Load API keys from PostgreSQL database instead of JSON file"""
        try:
            from services.database import db_service

            # Clear existing in-memory cache
            self.api_keys = {}
            self._key_lookup = {}

            # Query all API keys from database
            if not db_service.conn or db_service.conn.closed:
                if not db_service.connect():
                    logger.error("Failed to connect to database for loading API keys")
                    return

            query = """
                SELECT
                    ak.key_id, ak.client_id, ak.key_hash, ak.name, ak.description,
                    ak.created_at, ak.expires_at, ak.last_used_at, ak.is_active,
                    ak.created_by, ak.usage_count, ak.last_rotated_at,
                    ak.rotation_scheduled_at, ak.rotation_grace_end,
                    ak.token_template_name, ak.app_roles_overrides,
                    ak.token_ttl_minutes, ak.default_audience, ak.allowed_audiences
                FROM cids.api_keys ak
                ORDER BY ak.created_at DESC
            """

            db_service.cursor.execute(query)
            db_keys = db_service.cursor.fetchall()
            db_service.disconnect()

            total_loaded = 0
            for key_row in db_keys:
                client_id = key_row['client_id']
                key_id = key_row['key_id']

                # Convert database row to APIKeyMetadata format
                key_prefix = f"{API_KEY_PREFIX}{key_id[:8]}..."

                metadata = APIKeyMetadata(
                    key_id=key_id,
                    key_hash=key_row['key_hash'],
                    key_prefix=key_prefix,
                    name=key_row['name'] or f"API Key {key_id[:8]}",
                    permissions=[],  # Permissions are handled separately in v2.0
                    expires_at=key_row['expires_at'].isoformat() if key_row['expires_at'] else None,
                    created_at=key_row['created_at'].isoformat() if key_row['created_at'] else None,
                    created_by=key_row['created_by'] or 'unknown',
                    last_used_at=key_row['last_used_at'].isoformat() if key_row['last_used_at'] else None,
                    is_active=key_row['is_active'],
                    usage_count=key_row['usage_count'] or 0,
                    last_rotated_at=key_row['last_rotated_at'].isoformat() if key_row['last_rotated_at'] else None,
                    rotation_scheduled_at=key_row['rotation_scheduled_at'].isoformat() if key_row['rotation_scheduled_at'] else None,
                    rotation_grace_end=key_row['rotation_grace_end'].isoformat() if key_row['rotation_grace_end'] else None,
                    token_template_name=key_row['token_template_name'],
                    app_roles_overrides=key_row['app_roles_overrides'],
                    token_ttl_minutes=key_row['token_ttl_minutes'],
                    default_audience=key_row['default_audience'],
                    allowed_audiences=key_row['allowed_audiences']
                )

                # Add to in-memory cache for backward compatibility
                if client_id not in self.api_keys:
                    self.api_keys[client_id] = {}
                self.api_keys[client_id][key_id] = metadata

                # Add to key lookup for prefix-based validation
                if metadata.is_active:
                    self._key_lookup[key_prefix] = (client_id, key_id)

                total_loaded += 1

            logger.info(f"Loaded {total_loaded} API keys from database")

        except Exception as e:
            logger.error(f"Error loading API keys from database: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.api_keys = {}
            self._key_lookup = {}

    def _save_keys(self):
        """Save keys to database - this method is deprecated as we now save directly to DB"""
        logger.warning("_save_keys called but API keys are now saved directly to database in create/update operations")
        # This method is kept for backward compatibility but does nothing
        # All database updates now happen in individual methods

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
        # Use the actual key content after prefix as key_id for database
        key_id = api_key.replace(API_KEY_PREFIX, '')
        ttl_days = DEFAULT_EXPIRY_DAYS if ttl_days is None else min(ttl_days, MAX_EXPIRY_DAYS)
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

        # Save to database
        from services.database import db_service
        success = db_service.create_api_key(
            app_id=app_client_id,
            key_id=key_id,
            key_hash=self.hash_key(api_key),
            name=name,
            permissions=permissions,
            expires_at=expires_at.isoformat() if expires_at else None,
            created_by=created_by,
            token_template_name=token_template_name,
            app_roles_overrides=app_roles_overrides,
            token_ttl_minutes=token_ttl_minutes,
            default_audience=default_audience,
            allowed_audiences=allowed_audiences
        )

        if not success:
            raise Exception("Failed to save API key to database")

        # Create metadata for return
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

        # Also keep in memory for backward compatibility
        if app_client_id not in self.api_keys:
            self.api_keys[app_client_id] = {}
        self.api_keys[app_client_id][key_id] = metadata
        self._key_lookup[metadata.key_prefix] = (app_client_id, key_id)

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
        """Revoke an API key by updating database and in-memory cache"""
        if app_client_id not in self.api_keys:
            return False
        if key_id not in self.api_keys[app_client_id]:
            return False

        try:
            # Update database
            from services.database import db_service

            if not db_service.conn or db_service.conn.closed:
                if not db_service.connect():
                    logger.error("Failed to connect to database for revoking API key")
                    return False

            query = """
                UPDATE cids.api_keys
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE client_id = %s AND key_id = %s
            """

            db_service.cursor.execute(query, (app_client_id, key_id))
            db_service.conn.commit()
            db_service.disconnect()

            # Update in-memory cache
            self.api_keys[app_client_id][key_id].is_active = False
            key_prefix = self.api_keys[app_client_id][key_id].key_prefix
            if key_prefix in self._key_lookup:
                del self._key_lookup[key_prefix]

            logger.info(f"API key {key_id} revoked for app {app_client_id}")
            return True

        except Exception as e:
            logger.error(f"Error revoking API key in database: {e}")
            return False

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
        # Update database for old key rotation metadata
        try:
            from services.database import db_service

            if not db_service.conn or db_service.conn.closed:
                if not db_service.connect():
                    logger.error("Failed to connect to database for updating rotation metadata")
                    return new_key, new_metadata

            rotation_time = datetime.utcnow()
            grace_end_time = rotation_time + timedelta(hours=grace_period_hours)

            query = """
                UPDATE cids.api_keys
                SET last_rotated_at = %s, rotation_scheduled_at = %s, rotation_grace_end = %s
                WHERE client_id = %s AND key_id = %s
            """

            db_service.cursor.execute(query, (
                rotation_time,
                grace_end_time,
                grace_end_time,
                app_client_id,
                key_id
            ))
            db_service.conn.commit()
            db_service.disconnect()

            # Update in-memory cache
            old_key.last_rotated_at = rotation_time.isoformat()
            old_key.rotation_scheduled_at = grace_end_time.isoformat()
            old_key.rotation_grace_end = old_key.rotation_scheduled_at

        except Exception as e:
            logger.error(f"Error updating rotation metadata in database: {e}")
        return new_key, new_metadata

    def validate_api_key(self, api_key: str) -> Optional[Tuple[str, APIKeyMetadata]]:
        if not api_key.startswith(API_KEY_PREFIX):
            return None

        # First try database lookup for new keys
        from services.database import db_service
        import hashlib

        # Extract key_id from the API key (everything after cids_ak_)
        key_id = api_key.replace(API_KEY_PREFIX, '')

        # Check database first
        try:
            db_result = db_service.validate_api_key_in_db(key_id, api_key)
            if db_result and db_result is not False:
                # db_result is (client_id, name) tuple
                client_id, key_name = db_result
                # Create metadata from DB for compatibility
                metadata = APIKeyMetadata(
                    key_id=key_id,
                    key_prefix=api_key[:len(API_KEY_PREFIX) + 8],
                    key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
                    name=key_name,
                    permissions=[],
                    is_active=True,
                    created_at=datetime.utcnow().isoformat(),
                    created_by="system",
                    usage_count=1,
                    expires_at=None
                )
                logger.info(f"API key validated from database for client {client_id}")
                return client_id, metadata
        except Exception as e:
            logger.error(f"Database API key validation error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Fall back to memory lookup for old keys
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
                # Update database to mark as inactive
                try:
                    from services.database import db_service
                    if not db_service.conn or db_service.conn.closed:
                        db_service.connect()

                    query = """
                        UPDATE cids.api_keys
                        SET is_active = false
                        WHERE client_id = %s AND key_id = %s
                    """
                    db_service.cursor.execute(query, (app_client_id, key_id))
                    db_service.conn.commit()
                    db_service.disconnect()

                    metadata.is_active = False
                except Exception as db_e:
                    logger.error(f"Error updating database during grace period expiry: {db_e}")
                return None

        # Update last_used_at and usage_count in database
        try:
            from services.database import db_service
            if not db_service.conn or db_service.conn.closed:
                db_service.connect()

            query = """
                UPDATE cids.api_keys
                SET last_used_at = CURRENT_TIMESTAMP, usage_count = COALESCE(usage_count, 0) + 1
                WHERE client_id = %s AND key_id = %s
            """
            db_service.cursor.execute(query, (app_client_id, key_id))
            db_service.conn.commit()
            db_service.disconnect()

            # Update in-memory cache
            metadata.last_used_at = datetime.utcnow().isoformat()
            metadata.usage_count += 1

        except Exception as db_e:
            logger.error(f"Error updating API key usage in database: {db_e}")
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
            # Update database to remove expired keys
            try:
                from services.database import db_service
                if not db_service.conn or db_service.conn.closed:
                    db_service.connect()

                # Delete expired keys from database
                query = """
                    DELETE FROM cids.api_keys
                    WHERE (expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP)
                       OR (rotation_grace_end IS NOT NULL AND rotation_grace_end < CURRENT_TIMESTAMP AND is_active = false)
                """
                db_service.cursor.execute(query)
                db_service.conn.commit()
                db_service.disconnect()

            except Exception as e:
                logger.error(f"Error cleaning up expired keys in database: {e}")

            logger.info(f"Cleaned up {removed_count} expired API keys")
        return removed_count


api_key_manager = APIKeyManager()

