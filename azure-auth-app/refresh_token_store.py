"""
Refresh Token Storage and Management

In production, this would use Redis or a database.
For now, we'll use in-memory storage with TTL support.
"""
import time
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RefreshTokenStore:
    """Manages refresh token storage and validation"""
    
    def __init__(self):
        # In-memory storage: token_hash -> (user_info, expiry_timestamp)
        self.tokens: Dict[str, Tuple[dict, float]] = {}
        # Track token families for rotation
        self.token_families: Dict[str, str] = {}  # family_id -> latest_token_hash
        
    def create_refresh_token(self, user_info: dict, lifetime_days: int = 30) -> str:
        """
        Create a new refresh token
        
        Args:
            user_info: User information to associate with token
            lifetime_days: Token lifetime in days
            
        Returns:
            Refresh token string
        """
        # Generate a secure random token
        token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(token)
        
        # Calculate expiry
        expiry = time.time() + (lifetime_days * 24 * 60 * 60)
        
        # Generate family ID for token rotation
        family_id = user_info.get('family_id', secrets.token_urlsafe(16))
        user_info['family_id'] = family_id
        
        # Store token
        self.tokens[token_hash] = (user_info, expiry)
        self.token_families[family_id] = token_hash
        
        logger.info(f"Created refresh token for user {user_info.get('sub')} with family {family_id}")
        
        return token
    
    def validate_and_rotate(self, token: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Validate a refresh token and rotate it (one-time use)
        
        Args:
            token: Refresh token to validate
            
        Returns:
            Tuple of (user_info, new_refresh_token) or (None, None) if invalid
        """
        token_hash = self._hash_token(token)
        
        # Check if token exists
        if token_hash not in self.tokens:
            logger.warning("Refresh token not found")
            return None, None
        
        user_info, expiry = self.tokens[token_hash]
        
        # Check expiry
        if time.time() > expiry:
            logger.warning(f"Refresh token expired for user {user_info.get('sub')}")
            self._cleanup_token(token_hash)
            return None, None
        
        # Check token family (detect reuse of old tokens)
        family_id = user_info.get('family_id')
        if family_id and self.token_families.get(family_id) != token_hash:
            logger.error(f"Possible token replay attack detected for family {family_id}")
            # Revoke entire family
            self._revoke_family(family_id)
            return None, None
        
        # Token is valid - rotate it
        # Remove old token
        del self.tokens[token_hash]
        
        # Create new token
        new_token = self.create_refresh_token(user_info, lifetime_days=30)
        
        logger.info(f"Rotated refresh token for user {user_info.get('sub')}")
        
        return user_info, new_token
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a specific refresh token
        
        Args:
            token: Token to revoke
            
        Returns:
            True if token was found and revoked
        """
        token_hash = self._hash_token(token)
        
        if token_hash in self.tokens:
            self._cleanup_token(token_hash)
            return True
        
        return False
    
    def revoke_all_user_tokens(self, user_sub: str) -> int:
        """
        Revoke all refresh tokens for a user
        
        Args:
            user_sub: User subject identifier
            
        Returns:
            Number of tokens revoked
        """
        revoked = 0
        tokens_to_remove = []
        
        for token_hash, (user_info, _) in self.tokens.items():
            if user_info.get('sub') == user_sub:
                tokens_to_remove.append(token_hash)
        
        for token_hash in tokens_to_remove:
            self._cleanup_token(token_hash)
            revoked += 1
        
        logger.info(f"Revoked {revoked} tokens for user {user_sub}")
        return revoked
    
    def cleanup_expired(self) -> int:
        """
        Remove expired tokens
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = time.time()
        expired_tokens = []
        
        for token_hash, (_, expiry) in self.tokens.items():
            if current_time > expiry:
                expired_tokens.append(token_hash)
        
        for token_hash in expired_tokens:
            self._cleanup_token(token_hash)
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired refresh tokens")
        
        return len(expired_tokens)
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _cleanup_token(self, token_hash: str):
        """Remove a token and update family tracking"""
        if token_hash in self.tokens:
            user_info, _ = self.tokens[token_hash]
            family_id = user_info.get('family_id')
            
            # Remove from tokens
            del self.tokens[token_hash]
            
            # Update family tracking
            if family_id and self.token_families.get(family_id) == token_hash:
                del self.token_families[family_id]
    
    def _revoke_family(self, family_id: str):
        """Revoke all tokens in a family (security measure)"""
        tokens_to_remove = []
        
        for token_hash, (user_info, _) in self.tokens.items():
            if user_info.get('family_id') == family_id:
                tokens_to_remove.append(token_hash)
        
        for token_hash in tokens_to_remove:
            del self.tokens[token_hash]
        
        if family_id in self.token_families:
            del self.token_families[family_id]
        
        logger.warning(f"Revoked entire token family {family_id} ({len(tokens_to_remove)} tokens)")


# Global instance
refresh_token_store = RefreshTokenStore()