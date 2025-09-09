"""Resource filter policy (RLS-like) compiler and store (migrated)"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from utils.paths import data_path

logger = logging.getLogger(__name__)

FILTER_POLICIES_FILE = data_path("resource_filter_policies.json")


class ResourceFilterPolicyStore:
    def __init__(self):
        self.policies: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        try:
            if FILTER_POLICIES_FILE.exists():
                with open(FILTER_POLICIES_FILE, 'r') as f:
                    self.policies = json.load(f)
        except Exception as e:
            logger.error(f"Error loading filter policies: {e}")
            self.policies = {}

    def _save(self):
        try:
            FILTER_POLICIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FILTER_POLICIES_FILE, 'w') as f:
                json.dump(self.policies, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving filter policies: {e}")

    def upsert_policy(self, app_client_id: str, policy_id: str, policy: Dict) -> Dict:
        if app_client_id not in self.policies:
            self.policies[app_client_id] = {}
        self.policies[app_client_id][policy_id] = {
            'policy': policy,
            'updated_at': datetime.utcnow().isoformat(),
        }
        self._save()
        return {'app_client_id': app_client_id, 'policy_id': policy_id}

    def get_policy(self, app_client_id: str, policy_id: str) -> Optional[Dict]:
        return self.policies.get(app_client_id, {}).get(policy_id)


def compile_filter(policy: Dict[str, Any], user_attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Compile a policy into a concrete filter expression given user attrs"""
    # Placeholder simple compiler
    compiled = {}
    for resource, rules in policy.get('resources', {}).items():
        compiled[resource] = {}
        for field, condition in rules.get('fields', {}).items():
            if isinstance(condition, str) and condition.startswith('user.'):
                key = condition.split('.', 1)[1]
                compiled[resource][field] = user_attrs.get(key)
            else:
                compiled[resource][field] = condition
    return compiled

