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
        # In-memory storage for token activity logs
        # In production, this would be stored in a database
        self.activity_logs: Dict[str, List[Dict[str, Any]]] = {}
        
    def log_activity(self, 
                    token_id: str,
                    action: TokenAction,
                    performed_by: Optional[Dict[str, Any]] = None,
                    details: Optional[Dict[str, Any]] = None,
                    ip_address: Optional[str] = None,
                    user_agent: Optional[str] = None) -> str:
        """
        Log an activity for a specific token
        
        Args:
            token_id: The ID of the token
            action: The action performed
            performed_by: User info who performed the action (if different from token owner)
            details: Additional details about the action
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            The ID of the created log entry
        """
        log_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        log_entry = {
            'id': log_id,
            'timestamp': timestamp.isoformat() + 'Z',
            'action': action.value,
            'performed_by': performed_by,
            'details': details or {},
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        # Initialize the list if it doesn't exist
        if token_id not in self.activity_logs:
            self.activity_logs[token_id] = []
            
        # Add the log entry
        self.activity_logs[token_id].append(log_entry)
        
        logger.debug(f"Logged activity for token {token_id}: {action.value}")
        
        return log_id
        
    def get_token_activities(self, token_id: str) -> List[Dict[str, Any]]:
        """
        Get all activities for a specific token
        
        Args:
            token_id: The ID of the token
            
        Returns:
            List of activity log entries
        """
        return self.activity_logs.get(token_id, [])
        
    def get_all_activities(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all activities for all tokens
        
        Returns:
            Dictionary of token_id -> list of activities
        """
        return self.activity_logs.copy()
        
    def clear_token_activities(self, token_id: str):
        """
        Clear all activities for a specific token (used for testing)
        
        Args:
            token_id: The ID of the token
        """
        if token_id in self.activity_logs:
            del self.activity_logs[token_id]
            
    def get_user_activities(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get all activities performed by a specific user
        
        Args:
            user_email: Email of the user
            
        Returns:
            List of activity log entries
        """
        activities = []
        for token_id, token_activities in self.activity_logs.items():
            for activity in token_activities:
                performed_by = activity.get('performed_by', {})
                if performed_by and performed_by.get('email') == user_email:
                    activities.append({
                        'token_id': token_id,
                        **activity
                    })
        return activities

# Global instance
token_activity_logger = TokenActivityLogger()