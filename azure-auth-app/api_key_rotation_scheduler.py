"""
API Key Rotation Scheduler for CIDS

This module provides background task scheduling for automatic API key rotation
and cleanup of expired keys.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from api_key_manager import api_key_manager
from audit_logger import audit_logger, AuditAction
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration file for rotation policies
ROTATION_POLICY_FILE = Path("app_data/rotation_policies.json")

class APIKeyRotationScheduler:
    """Manages automatic API key rotation and cleanup"""
    
    def __init__(self):
        self.running = False
        self.rotation_policies = {}
        self._load_policies()
    
    def _load_policies(self):
        """Load rotation policies from configuration"""
        try:
            if ROTATION_POLICY_FILE.exists():
                with open(ROTATION_POLICY_FILE, 'r') as f:
                    self.rotation_policies = json.load(f)
            else:
                # Default policies
                self.rotation_policies = {
                    "default": {
                        "days_before_expiry": 7,
                        "grace_period_hours": 24,
                        "auto_rotate": True,
                        "notify_webhook": None
                    }
                }
                self._save_policies()
        except Exception as e:
            logger.error(f"Error loading rotation policies: {e}")
            self.rotation_policies = {}
    
    def _save_policies(self):
        """Save rotation policies to configuration"""
        try:
            ROTATION_POLICY_FILE.parent.mkdir(exist_ok=True)
            with open(ROTATION_POLICY_FILE, 'w') as f:
                json.dump(self.rotation_policies, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving rotation policies: {e}")
    
    def set_app_rotation_policy(self, app_client_id: str, 
                               days_before_expiry: int = 7,
                               grace_period_hours: int = 24,
                               auto_rotate: bool = True,
                               notify_webhook: Optional[str] = None):
        """Set rotation policy for a specific app"""
        self.rotation_policies[app_client_id] = {
            "days_before_expiry": days_before_expiry,
            "grace_period_hours": grace_period_hours,
            "auto_rotate": auto_rotate,
            "notify_webhook": notify_webhook
        }
        self._save_policies()
        logger.info(f"Updated rotation policy for app {app_client_id}")
    
    def get_app_rotation_policy(self, app_client_id: str) -> dict:
        """Get rotation policy for an app"""
        return self.rotation_policies.get(app_client_id, 
                                         self.rotation_policies.get("default", {}))
    
    async def check_and_rotate_keys(self):
        """Check for keys needing rotation and rotate them if policy allows"""
        logger.info("Checking for API keys needing rotation...")
        
        rotation_count = 0
        notification_queue = []
        
        # Get all keys approaching expiry
        for app_id, key_id, metadata in api_key_manager.get_keys_needing_rotation():
            policy = self.get_app_rotation_policy(app_id)
            
            if not policy.get('auto_rotate', False):
                # Just add to notification queue
                notification_queue.append({
                    'app_id': app_id,
                    'key_id': key_id,
                    'key_name': metadata.name,
                    'expires_at': metadata.expires_at,
                    'action': 'manual_rotation_needed'
                })
                logger.info(f"Key {key_id} for app {app_id} needs rotation but auto-rotate is disabled")
                continue
            
            # Auto-rotate the key
            try:
                grace_period = policy.get('grace_period_hours', 24)
                result = api_key_manager.rotate_api_key(
                    app_client_id=app_id,
                    key_id=key_id,
                    created_by="system:auto-rotation",
                    grace_period_hours=grace_period
                )
                
                if result:
                    new_key, new_metadata = result
                    rotation_count += 1
                    
                    # Log the rotation
                    audit_logger.log_action(
                        action=AuditAction.API_KEY_ROTATED,
                        user_email="system@auto-rotation",
                        resource_type="api_key",
                        resource_id=key_id,
                        details={
                            "app_client_id": app_id,
                            "new_key_id": new_metadata.key_id,
                            "grace_period_hours": grace_period,
                            "auto_rotation": True
                        }
                    )
                    
                    # Add to notification queue
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
                notification_queue.append({
                    'app_id': app_id,
                    'key_id': key_id,
                    'key_name': metadata.name,
                    'error': str(e),
                    'action': 'rotation_failed'
                })
        
        # Process notifications
        await self._send_notifications(notification_queue)
        
        if rotation_count > 0:
            logger.info(f"Auto-rotated {rotation_count} API keys")
        
        return rotation_count
    
    async def cleanup_expired_keys(self):
        """Remove expired and inactive keys"""
        logger.info("Cleaning up expired API keys...")
        
        removed_count = api_key_manager.cleanup_expired_keys()
        
        if removed_count > 0:
            # Log the cleanup
            audit_logger.log_action(
                action=AuditAction.API_KEY_EXPIRED,
                user_email="system@cleanup",
                resource_type="api_key",
                details={
                    "removed_count": removed_count,
                    "cleanup_time": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Cleaned up {removed_count} expired API keys")
        
        return removed_count
    
    async def _send_notifications(self, notifications: list):
        """Send notifications about key rotations (placeholder for future webhook integration)"""
        if not notifications:
            return
        
        # Log notifications for now (future: send to webhook/email/slack)
        logger.info(f"Rotation notifications: {len(notifications)} events")
        
        # Save to notification log file for now
        notification_file = Path("app_data/rotation_notifications.jsonl")
        try:
            notification_file.parent.mkdir(exist_ok=True)
            with open(notification_file, 'a') as f:
                for notification in notifications:
                    notification['timestamp'] = datetime.utcnow().isoformat()
                    f.write(json.dumps(notification) + '\n')
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
        
        # Future: Implement webhook calls
        for notification in notifications:
            app_id = notification.get('app_id')
            policy = self.get_app_rotation_policy(app_id)
            webhook_url = policy.get('notify_webhook')
            
            if webhook_url:
                # TODO: Implement webhook call
                logger.info(f"Would send notification to webhook: {webhook_url}")
    
    async def run_scheduler(self, check_interval_hours: int = 6):
        """Run the rotation scheduler in the background"""
        self.running = True
        logger.info(f"Starting API key rotation scheduler (checking every {check_interval_hours} hours)")
        
        while self.running:
            try:
                # Check and rotate keys
                await self.check_and_rotate_keys()
                
                # Cleanup expired keys
                await self.cleanup_expired_keys()
                
                # Wait for next check
                await asyncio.sleep(check_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in rotation scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the rotation scheduler"""
        self.running = False
        logger.info("Stopping API key rotation scheduler")


# Global scheduler instance
rotation_scheduler = APIKeyRotationScheduler()


# Endpoint to manually trigger rotation check (for admin use)
async def manual_rotation_check():
    """Manually trigger rotation check"""
    rotated = await rotation_scheduler.check_and_rotate_keys()
    cleaned = await rotation_scheduler.cleanup_expired_keys()
    
    return {
        "rotated_keys": rotated,
        "cleaned_keys": cleaned,
        "timestamp": datetime.utcnow().isoformat()
    }


# Function to start scheduler as background task
def start_rotation_scheduler(app, check_interval_hours: int = 6):
    """Start the rotation scheduler as a background task in FastAPI"""
    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(rotation_scheduler.run_scheduler(check_interval_hours))
        logger.info("API key rotation scheduler started")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        rotation_scheduler.stop()
        logger.info("API key rotation scheduler stopped")