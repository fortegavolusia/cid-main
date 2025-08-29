"""Audit logging for CIDS IAM operations (migrated)"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

from backend.utils.paths import logs_path

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    APP_REGISTERED = "app.registered"
    APP_UPDATED = "app.updated"
    APP_DELETED = "app.deleted"
    ENDPOINTS_UPDATED = "endpoints.updated"
    ENDPOINTS_DELETED = "endpoints.deleted"
    ROLES_UPDATED = "roles.updated"
    ROLE_MAPPINGS_UPDATED = "role_mappings.updated"
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"
    POLICY_CREATED = "policy.created"
    POLICY_UPDATED = "policy.updated"
    POLICY_ACTIVATED = "policy.activated"
    TOKEN_ISSUED = "token.issued"
    TOKEN_REFRESHED = "token.refreshed"
    TOKEN_REVOKED = "token.revoked"
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    DISCOVERY_TRIGGERED = "discovery.triggered"
    DISCOVERY_COMPLETED = "discovery.completed"
    DISCOVERY_FAILED = "discovery.failed"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    TOKEN_TEMPLATE_UPDATED = "token_template.updated"
    TOKEN_TEMPLATE_DELETED = "token_template.deleted"
    TOKEN_TEMPLATES_IMPORTED = "token_templates.imported"
    API_KEY_ROTATED = "api_key.rotated"
    API_KEY_USED = "api_key.used"
    API_KEY_EXPIRED = "api_key.expired"


class AuditLogger:
    def __init__(self):
        self.audit_dir = logs_path("audit")
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.current_date = None

    def _get_audit_file(self):
        today = datetime.utcnow().date()
        if today != self.current_date:
            self.current_date = today
            self.current_file = self.audit_dir / f"audit_{today.isoformat()}.jsonl"
        return self.current_file

    def log_action(self, action: AuditAction, user_email: Optional[str] = None, user_id: Optional[str] = None, resource_type: Optional[str] = None, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action.value,
                "user": {"email": user_email, "id": user_id},
                "resource": {"type": resource_type, "id": resource_id},
                "details": details or {},
                "context": {"ip_address": ip_address, "user_agent": user_agent},
            }
            audit_entry = self._remove_none_values(audit_entry)
            audit_file = self._get_audit_file()
            with open(audit_file, 'a') as f:
                f.write(json.dumps(audit_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _remove_none_values(self, d: Dict) -> Dict:
        if not isinstance(d, dict):
            return d
        return {k: self._remove_none_values(v) for k, v in d.items() if v is not None and (not isinstance(v, dict) or self._remove_none_values(v))}

    def query_audit_logs(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, action: Optional[AuditAction] = None, user_email: Optional[str] = None, resource_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        results = []
        dates_to_check = None
        if start_date and end_date:
            dates_to_check = []
            current = start_date.date()
            while current <= end_date.date():
                dates_to_check.append(current)
                current = current + timedelta(days=1)
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
                        if action and entry.get('action') != action.value:
                            continue
                        if user_email and entry.get('user', {}).get('email') != user_email:
                            continue
                        if resource_id and entry.get('resource', {}).get('id') != resource_id:
                            continue
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


audit_logger = AuditLogger()

