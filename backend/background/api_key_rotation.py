"""API Key Rotation Scheduler (migrated)"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
import json

from backend.services.api_keys import api_key_manager, APIKeyTTL
from backend.services.audit import audit_logger, AuditAction
from backend.utils.paths import data_path

logger = logging.getLogger(__name__)

ROTATION_POLICY_FILE = data_path("rotation_policies.json")
NOTIFICATIONS_FILE = data_path("rotation_notifications.jsonl")


class APIKeyRotationScheduler:
    def __init__(self):
        self.running = False
        self.rotation_policies = {}
        self._load_policies()

    def _load_policies(self):
        try:
            if ROTATION_POLICY_FILE.exists():
                with open(ROTATION_POLICY_FILE, 'r') as f:
                    self.rotation_policies = json.load(f)
            else:
                self.rotation_policies = {
                    "default": {
                        "days_before_expiry": 7,
                        "grace_period_hours": 24,
                        "auto_rotate": True,
                        "notify_webhook": None,
                    }
                }
                self._save_policies()
        except Exception as e:
            logger.error(f"Error loading rotation policies: {e}")
            self.rotation_policies = {}

    def _save_policies(self):
        try:
            ROTATION_POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ROTATION_POLICY_FILE, 'w') as f:
                json.dump(self.rotation_policies, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving rotation policies: {e}")

    def set_app_rotation_policy(self, app_client_id: str, days_before_expiry: int = 7, grace_period_hours: int = 24, auto_rotate: bool = True, notify_webhook: Optional[str] = None):
        self.rotation_policies[app_client_id] = {
            "days_before_expiry": days_before_expiry,
            "grace_period_hours": grace_period_hours,
            "auto_rotate": auto_rotate,
            "notify_webhook": notify_webhook,
        }
        self._save_policies()
        logger.info(f"Updated rotation policy for app {app_client_id}")

    def get_app_rotation_policy(self, app_client_id: str) -> dict:
        return self.rotation_policies.get(app_client_id, self.rotation_policies.get("default", {}))

    async def check_and_rotate_keys(self):
        logger.info("Checking for API keys needing rotation...")
        rotation_count = 0
        notification_queue = []
        for app_id, key_id, metadata in api_key_manager.get_keys_needing_rotation():
            policy = self.get_app_rotation_policy(app_id)
            if not policy.get('auto_rotate', False):
                notification_queue.append({
                    'app_id': app_id,
                    'key_id': key_id,
                    'key_name': metadata.name,
                    'expires_at': metadata.expires_at,
                    'action': 'manual_rotation_needed'
                })
                logger.info(f"Key {key_id} for app {app_id} needs rotation but auto-rotate is disabled")
                continue
            try:
                grace_period = policy.get('grace_period_hours', 24)
                result = api_key_manager.rotate_api_key(app_client_id=app_id, key_id=key_id, created_by="system:auto-rotation", grace_period_hours=grace_period)
                if result:
                    new_key, new_metadata = result
                    rotation_count += 1
                    audit_logger.log_action(
                        action=AuditAction.API_KEY_ROTATED,
                        user_email="system@auto-rotation",
                        resource_type="api_key",
                        resource_id=key_id,
                        details={
                            "app_client_id": app_id,
                            "new_key_id": new_metadata.key_id,
                            "grace_period_hours": grace_period,
                            "auto_rotation": True,
                        },
                    )
                    notification_queue.append({
                        'app_id': app_id,
                        'old_key_id': key_id,
                        'new_key_id': new_metadata.key_id,
                        'key_name': metadata.name,
                        'grace_period_hours': grace_period,
                        'action': 'auto_rotated'
                    })
                    logger.info(f"Successfully auto-rotated key {key_id} for app {app_id}")
            except Exception as e:
                logger.error(f"Error rotating key {key_id} for app {app_id}: {e}")
                notification_queue.append({'app_id': app_id, 'key_id': key_id, 'key_name': metadata.name, 'error': str(e), 'action': 'rotation_failed'})
        await self._send_notifications(notification_queue)
        if rotation_count > 0:
            logger.info(f"Auto-rotated {rotation_count} API keys")
        return rotation_count

    async def cleanup_expired_keys(self):
        logger.info("Cleaning up expired API keys...")
        removed_count = api_key_manager.cleanup_expired_keys()
        if removed_count > 0:
            audit_logger.log_action(action=AuditAction.API_KEY_EXPIRED, user_email="system@cleanup", resource_type="api_key", details={"removed_count": removed_count, "cleanup_time": datetime.utcnow().isoformat()})
            logger.info(f"Cleaned up {removed_count} expired API keys")
        return removed_count

    async def _send_notifications(self, notifications: list):
        if not notifications:
            return
        logger.info(f"Rotation notifications: {len(notifications)} events")
        try:
            NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(NOTIFICATIONS_FILE, 'a') as f:
                for notification in notifications:
                    notification['timestamp'] = datetime.utcnow().isoformat()
                    f.write(json.dumps(notification) + '\n')
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
        # Placeholder for webhook integration

    async def run_scheduler(self, check_interval_hours: int = 6):
        self.running = True
        logger.info(f"Starting API key rotation scheduler (checking every {check_interval_hours} hours)")
        while self.running:
            try:
                await self.check_and_rotate_keys()
                await self.cleanup_expired_keys()
                await asyncio.sleep(check_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Error in rotation scheduler: {e}")
                await asyncio.sleep(300)

    def stop(self):
        self.running = False
        logger.info("Stopping API key rotation scheduler")


rotation_scheduler = APIKeyRotationScheduler()


async def manual_rotation_check():
    rotated = await rotation_scheduler.check_and_rotate_keys()
    cleaned = await rotation_scheduler.cleanup_expired_keys()
    return {"rotated_keys": rotated, "cleaned_keys": cleaned, "timestamp": datetime.utcnow().isoformat()}


def start_rotation_scheduler(app, check_interval_hours: int = 6):
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(rotation_scheduler.run_scheduler(check_interval_hours))
        logger.info("API key rotation scheduler started")

    @app.on_event("shutdown")
    async def shutdown_event():
        rotation_scheduler.stop()
        logger.info("API key rotation scheduler stopped")

