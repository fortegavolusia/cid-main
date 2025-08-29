"""Refresh Token Storage and Management (migrated, in-memory)"""
import time
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RefreshTokenStore:
    def __init__(self):
        self.tokens: Dict[str, Tuple[dict, float]] = {}
        self.token_families: Dict[str, str] = {}

    def create_refresh_token(self, user_info: dict, lifetime_days: int = 30) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(token)
        expiry = time.time() + (lifetime_days * 24 * 60 * 60)
        family_id = user_info.get('family_id', secrets.token_urlsafe(16))
        user_info['family_id'] = family_id
        self.tokens[token_hash] = (user_info, expiry)
        self.token_families[family_id] = token_hash
        return token

    def validate_and_rotate(self, token: str) -> Tuple[Optional[dict], Optional[str]]:
        token_hash = self._hash_token(token)
        if token_hash not in self.tokens:
            return None, None
        user_info, expiry = self.tokens[token_hash]
        if time.time() > expiry:
            self._cleanup_token(token_hash)
            return None, None
        family_id = user_info.get('family_id')
        if family_id and self.token_families.get(family_id) != token_hash:
            self._revoke_family(family_id)
            return None, None
        del self.tokens[token_hash]
        new_token = self.create_refresh_token(user_info, lifetime_days=30)
        return user_info, new_token

    def revoke_token(self, token: str) -> bool:
        token_hash = self._hash_token(token)
        if token_hash in self.tokens:
            self._cleanup_token(token_hash)
            return True
        return False

    def revoke_all_user_tokens(self, user_sub: str) -> int:
        revoked = 0
        tokens_to_remove = [h for h, (info, _) in self.tokens.items() if info.get('sub') == user_sub]
        for token_hash in tokens_to_remove:
            self._cleanup_token(token_hash)
            revoked += 1
        return revoked

    def cleanup_expired(self) -> int:
        current_time = time.time()
        expired_tokens = [h for h, (_, exp) in self.tokens.items() if current_time > exp]
        for token_hash in expired_tokens:
            self._cleanup_token(token_hash)
        return len(expired_tokens)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _cleanup_token(self, token_hash: str):
        if token_hash in self.tokens:
            user_info, _ = self.tokens[token_hash]
            family_id = user_info.get('family_id')
            del self.tokens[token_hash]
            if family_id and self.token_families.get(family_id) == token_hash:
                del self.token_families[family_id]

    def _revoke_family(self, family_id: str):
        tokens_to_remove = [h for h, (info, _) in self.tokens.items() if info.get('family_id') == family_id]
        for token_hash in tokens_to_remove:
            del self.tokens[token_hash]
        if family_id in self.token_families:
            del self.token_families[family_id]


refresh_token_store = RefreshTokenStore()

