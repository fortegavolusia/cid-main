"""Token activity logging (migrated, in-memory)"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TokenAction(Enum):
    CREATED = "created"
    REFRESHED = "refreshed"
    VALIDATED = "validated"
    REVOKED = "revoked"
    EXPIRED = "expired"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    ADMIN_VIEW = "admin_view"
    ADMIN_ACTION = "admin_action"


class TokenActivityLogger:
    def __init__(self):
        self.activity_logs: Dict[str, List[Dict[str, Any]]] = {}

    def log_activity(self, token_id: str, action: TokenAction, performed_by: Optional[Dict[str, Any]] = None, details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        from backend.libs.logging_config import get_logging_config
        from backend.services.token_activity_persist import append_token_activity

        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + 'Z'
        log_entry = {
            'id': log_id,
            'timestamp': timestamp,
            'event.category': 'token_activity',
            'token_id': token_id,
            'action': action.value,
            'performed_by': performed_by,
            'details': details or {},
            'ip_address': ip_address,
            'user_agent': user_agent,
        }
        if token_id not in self.activity_logs:
            self.activity_logs[token_id] = []
        self.activity_logs[token_id].append(log_entry)

        # Persist to disk if enabled
        cfg = get_logging_config()
        if cfg.get('token_activity', {}).get('enabled', True):
            append_token_activity(log_entry)

        logger.debug(f"Logged activity for token {token_id}: {action.value}")
        return log_id

    def get_token_activities(self, token_id: str) -> List[Dict[str, Any]]:
        return self.activity_logs.get(token_id, [])

    def get_all_activities(self) -> Dict[str, List[Dict[str, Any]]]:
        return self.activity_logs.copy()

    def clear_token_activities(self, token_id: str):
        if token_id in self.activity_logs:
            del self.activity_logs[token_id]

    def get_user_activities(self, user_email: str) -> List[Dict[str, Any]]:
        activities = []
        for token_id, token_activities in self.activity_logs.items():
            for activity in token_activities:
                performed_by = activity.get('performed_by', {})
                if performed_by and performed_by.get('email') == user_email:
                    activities.append({'token_id': token_id, **activity})
        return activities


token_activity_logger = TokenActivityLogger()

