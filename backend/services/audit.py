"""Audit logging for CIDS IAM operations (migrated)"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging
from enum import Enum
import httpx

from utils.paths import logs_path
from services.database import db_service

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    APP_CREATED = "app.created"
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
    ROLE_ACTIVATED = "role.activated"
    ROLE_DEACTIVATED = "role.deactivated"
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
    A2A_PERMISSION_CREATED = "a2a_permission.created"
    A2A_PERMISSION_UPDATED = "a2a_permission.updated"
    A2A_PERMISSION_DELETED = "a2a_permission.deleted"


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
            # Generate UUID with 'log' prefix from UUID service
            activity_id = None
            try:
                with httpx.Client() as client:
                    response = client.post(
                        "http://uuid-service-dev:8002/generate",
                        json={
                            "type": "custom",
                            "prefix": "log",
                            "format": "uuid_v4",
                            "requestor": "cids_audit",
                            "description": f"Activity log for {action.value}"
                        }
                    )
                    if response.status_code == 200:
                        activity_id = response.json().get("id")
            except Exception as e:
                logger.warning(f"Could not get UUID from service: {e}, using fallback")
                import uuid
                activity_id = f"log_{uuid.uuid4().hex[:16]}"
            
            # Log to database - ensure connection is established
            if not db_service.conn or db_service.conn.closed:
                # Force reconnection with correct parameters
                db_service.connection_params = {
                    'host': 'localhost',
                    'port': 54322,
                    'database': 'postgres',
                    'user': 'postgres',
                    'password': 'postgres'
                }
                if not db_service.connect():
                    logger.error(f"Failed to connect to database for audit logging")
                    return
            
            # Extract entity_name from details if available
            entity_name = None
            if details:
                entity_name = details.get('key_name') or details.get('name') or details.get('entity_name')

            result = db_service.log_activity(
                activity_id=activity_id,
                activity_type=action.value,
                entity_type=resource_type,
                entity_id=resource_id,
                entity_name=entity_name,
                user_email=user_email,
                user_id=user_id,
                details=details,
                status="success",
                error_message=None,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=None,
                api_endpoint=None,
                http_method=None,
                response_time_ms=None,
                request_id=None
            )
            
            if result:
                logger.info(f"Activity logged to database: {action.value} with ID {activity_id}")
            else:
                logger.error(f"Failed to log activity to database: {action.value}")
            
            # REMOVED: No longer writing to JSONL files - only database
            # All logs must go to database per requirements
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

