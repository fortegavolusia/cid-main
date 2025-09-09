"""Policy store and activation tracking (migrated)"""
from typing import Dict, Optional, List, Any
from datetime import datetime
import json
import logging
from pydantic import BaseModel, Field

from utils.paths import data_path

logger = logging.getLogger(__name__)

POLICY_FILE = data_path("policies.json")
ACTIVE_POLICY_FILE = data_path("active_policy.json")


# Compatibility models (align with legacy interface)
class Permission(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    resource: Optional[str] = None
    actions: List[str] = []


class RolePermissionMapping(BaseModel):
    role: str
    permissions: List[str]


class ABACRule(BaseModel):
    name: str
    description: str
    condition: str
    permissions: List[str]


class PolicyDocument(BaseModel):
    permissions: List[Permission]
    role_permission_matrix: List[RolePermissionMapping]
    abac_rules: Optional[List[ABACRule]] = []
    version: Optional[str] = None
    description: Optional[str] = None


class PolicyManager:
    def __init__(self):
        self.policies: Dict[str, Dict] = {}
        self.active_policy_id: Optional[str] = None
        self._load()

    def _load(self):
        try:
            if POLICY_FILE.exists():
                with open(POLICY_FILE, 'r') as f:
                    self.policies = json.load(f)
            if ACTIVE_POLICY_FILE.exists():
                with open(ACTIVE_POLICY_FILE, 'r') as f:
                    data = json.load(f)
                    self.active_policy_id = data.get('active_policy_id')
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            self.policies = {}
            self.active_policy_id = None

    def _save(self):
        try:
            POLICY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(POLICY_FILE, 'w') as f:
                json.dump(self.policies, f, indent=2)
            with open(ACTIVE_POLICY_FILE, 'w') as f:
                json.dump({"active_policy_id": self.active_policy_id}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving policies: {e}")

    def upsert_policy(self, policy_id: str, rules: Dict) -> Dict:
        self.policies[policy_id] = {
            'rules': rules,
            'updated_at': datetime.utcnow().isoformat(),
        }
        self._save()
        return {'policy_id': policy_id, 'updated_at': self.policies[policy_id]['updated_at']}

    def get_policy(self, policy_id: str) -> Optional[Dict]:
        return self.policies.get(policy_id)

    def activate_policy(self, policy_id: str) -> bool:
        if policy_id not in self.policies:
            return False
        self.active_policy_id = policy_id
        self._save()
        return True

    def get_active_policy(self) -> Optional[Dict]:
        if not self.active_policy_id:
            return None
        return self.get_policy(self.active_policy_id)

