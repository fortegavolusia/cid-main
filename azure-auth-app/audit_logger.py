"""Audit logging for CIDS IAM operations"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AuditAction(Enum):
    """Audit action types"""
    # App management
    APP_REGISTERED = "app.registered"
    APP_UPDATED = "app.updated"
    APP_DELETED = "app.deleted"
    
    # Endpoints
    ENDPOINTS_UPDATED = "endpoints.updated"
    ENDPOINTS_DELETED = "endpoints.deleted"
    
    # Roles
    ROLES_UPDATED = "roles.updated"
    ROLE_MAPPINGS_UPDATED = "role_mappings.updated"
    
    # Policy
    POLICY_CREATED = "policy.created"
    POLICY_UPDATED = "policy.updated"
    POLICY_ACTIVATED = "policy.activated"
    
    # Authentication
    TOKEN_ISSUED = "token.issued"
    TOKEN_REFRESHED = "token.refreshed"
    TOKEN_REVOKED = "token.revoked"
    
    # Access
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"

class AuditLogger:
    """Handles audit logging for IAM operations"""
    
    def __init__(self, data_dir: str = "app_data"):
        self.data_dir = Path(data_dir)
        self.audit_dir = self.data_dir / "audit"
        self.audit_dir.mkdir(exist_ok=True, parents=True)
        self.current_file = None
        self.current_date = None
    
    def _get_audit_file(self) -> Path:
        """Get current audit file (rotates daily)"""
        today = datetime.utcnow().date()
        if today != self.current_date:
            self.current_date = today
            self.current_file = self.audit_dir / f"audit_{today.isoformat()}.jsonl"
        return self.current_file
    
    def log_action(self, 
                   action: AuditAction,
                   user_email: Optional[str] = None,
                   user_id: Optional[str] = None,
                   resource_type: Optional[str] = None,
                   resource_id: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None) -> None:
        """Log an audit action"""
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action.value,
                "user": {
                    "email": user_email,
                    "id": user_id
                },
                "resource": {
                    "type": resource_type,
                    "id": resource_id
                },
                "details": details or {},
                "context": {
                    "ip_address": ip_address,
                    "user_agent": user_agent
                }
            }
            
            # Remove None values
            audit_entry = self._remove_none_values(audit_entry)
            
            # Write to audit file (append mode, one JSON per line)
            audit_file = self._get_audit_file()
            with open(audit_file, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _remove_none_values(self, d: Dict) -> Dict:
        """Recursively remove None values from dict"""
        if not isinstance(d, dict):
            return d
        
        return {
            k: self._remove_none_values(v)
            for k, v in d.items()
            if v is not None and (not isinstance(v, dict) or self._remove_none_values(v))
        }
    
    def query_audit_logs(self, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        action: Optional[AuditAction] = None,
                        user_email: Optional[str] = None,
                        resource_id: Optional[str] = None,
                        limit: int = 100) -> List[Dict]:
        """Query audit logs with filters"""
        results = []
        
        # Determine which files to search
        if start_date and end_date:
            dates_to_check = []
            current = start_date.date()
            while current <= end_date.date():
                dates_to_check.append(current)
                current = current + timedelta(days=1)
        else:
            # Check all files
            dates_to_check = None
        
        # Search through audit files
        for audit_file in sorted(self.audit_dir.glob("audit_*.jsonl"), reverse=True):
            if dates_to_check:
                file_date = audit_file.stem.split('_')[1]
                if file_date not in [d.isoformat() for d in dates_to_check]:
                    continue
            
            try:
                with open(audit_file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        entry = json.loads(line)
                        
                        # Apply filters
                        if action and entry.get('action') != action.value:
                            continue
                        if user_email and entry.get('user', {}).get('email') != user_email:
                            continue
                        if resource_id and entry.get('resource', {}).get('id') != resource_id:
                            continue
                        
                        # Check date range
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if start_date and entry_time < start_date:
                            continue
                        if end_date and entry_time > end_date:
                            continue
                        
                        results.append(entry)
                        
                        if len(results) >= limit:
                            return results
            
            except Exception as e:
                logger.error(f"Error reading audit file {audit_file}: {e}")
        
        return results

# Global audit logger instance
audit_logger = AuditLogger()