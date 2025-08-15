"""Policy management for CIDS"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
    condition: str  # e.g., "attrs.department == 'IT' AND attrs.level >= 3"
    permissions: List[str]

class PolicyDocument(BaseModel):
    permissions: List[Permission]
    role_permission_matrix: List[RolePermissionMapping]
    abac_rules: Optional[List[ABACRule]] = []
    version: Optional[str] = None
    description: Optional[str] = None

class PolicyManager:
    """Manages policy documents for apps"""
    
    def __init__(self, data_dir: str = "app_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.policies_dir = self.data_dir / "policies"
        self.policies_dir.mkdir(exist_ok=True)
        self.active_policies_file = self.data_dir / "active_policies.json"
        self.active_policies: Dict[str, str] = self._load_active_policies()
    
    def _load_active_policies(self) -> Dict[str, str]:
        """Load active policy versions"""
        if self.active_policies_file.exists():
            try:
                with open(self.active_policies_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading active policies: {e}")
                return {}
        return {}
    
    def _save_active_policies(self):
        """Save active policy versions"""
        with open(self.active_policies_file, 'w') as f:
            json.dump(self.active_policies, f, indent=2)
    
    def _get_policy_file(self, app_client_id: str, version: str) -> Path:
        """Get path to a specific policy version file"""
        return self.policies_dir / f"{app_client_id}_{version}.json"
    
    def upsert_policy(self, app_client_id: str, policy: PolicyDocument, updated_by: str) -> Dict:
        """Create or update policy for an app"""
        # Validate role names in matrix
        role_names = {rpm.role for rpm in policy.role_permission_matrix}
        permission_names = {p.name for p in policy.permissions}
        
        # Validate all permissions in role mappings exist
        for rpm in policy.role_permission_matrix:
            for perm in rpm.permissions:
                if perm not in permission_names:
                    raise ValueError(f"Permission '{perm}' not found in permissions list")
        
        # Generate version if not provided
        version = policy.version or datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # Save policy document
        policy_data = {
            **policy.dict(),
            'version': version,
            'app_client_id': app_client_id,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': updated_by
        }
        
        policy_file = self._get_policy_file(app_client_id, version)
        with open(policy_file, 'w') as f:
            json.dump(policy_data, f, indent=2)
        
        # Set as active version
        self.active_policies[app_client_id] = version
        self._save_active_policies()
        
        return {
            'app_client_id': app_client_id,
            'version': version,
            'permissions_count': len(policy.permissions),
            'roles_count': len(role_names),
            'abac_rules_count': len(policy.abac_rules) if policy.abac_rules else 0,
            'created_at': policy_data['created_at']
        }
    
    def get_active_policy(self, app_client_id: str) -> Optional[Dict]:
        """Get the active policy for an app"""
        version = self.active_policies.get(app_client_id)
        if not version:
            return None
        
        policy_file = self._get_policy_file(app_client_id, version)
        if not policy_file.exists():
            return None
        
        try:
            with open(policy_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading policy: {e}")
            return None
    
    def get_policy_version(self, app_client_id: str, version: str) -> Optional[Dict]:
        """Get a specific version of a policy"""
        policy_file = self._get_policy_file(app_client_id, version)
        if not policy_file.exists():
            return None
        
        try:
            with open(policy_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading policy version: {e}")
            return None
    
    def list_policy_versions(self, app_client_id: str) -> List[Dict]:
        """List all versions of a policy for an app"""
        versions = []
        for policy_file in self.policies_dir.glob(f"{app_client_id}_*.json"):
            version = policy_file.stem.split('_', 1)[1]
            try:
                with open(policy_file, 'r') as f:
                    data = json.load(f)
                    versions.append({
                        'version': version,
                        'created_at': data.get('created_at'),
                        'created_by': data.get('created_by'),
                        'is_active': version == self.active_policies.get(app_client_id)
                    })
            except Exception as e:
                logger.error(f"Error reading policy file {policy_file}: {e}")
        
        return sorted(versions, key=lambda x: x['created_at'], reverse=True)
    
    def compute_effective_permissions(self, app_client_id: str, roles: List[str], 
                                    attrs: Optional[Dict[str, Any]] = None) -> List[str]:
        """Compute effective permissions based on roles and attributes"""
        policy = self.get_active_policy(app_client_id)
        if not policy:
            return []
        
        permissions = set()
        
        # Add role-based permissions
        for rpm in policy.get('role_permission_matrix', []):
            if rpm['role'] in roles:
                permissions.update(rpm['permissions'])
        
        # Add ABAC permissions if attributes provided
        if attrs and policy.get('abac_rules'):
            for rule in policy['abac_rules']:
                try:
                    if self._evaluate_condition(rule['condition'], attrs):
                        permissions.update(rule['permissions'])
                except NotImplementedError:
                    logger.warning(
                        f"Skipping ABAC rule '{rule['name']}': ABAC evaluation not implemented. "
                        "Please implement _evaluate_condition() method for production use."
                    )
                    # Skip ABAC rules but continue with role-based permissions
                    continue
                except Exception as e:
                    logger.warning(f"Error evaluating ABAC rule {rule['name']}: {e}")
        
        return list(permissions)
    
    def _evaluate_condition(self, condition: str, attrs: Dict[str, Any]) -> bool:
        """Evaluate ABAC condition
        
        Args:
            condition: The condition string to evaluate
            attrs: User attributes to evaluate against
            
        Returns:
            bool: Whether the condition is satisfied
            
        Raises:
            NotImplementedError: ABAC condition evaluation not yet implemented
        """
        raise NotImplementedError(
            "ABAC condition evaluation is not yet implemented. "
            "For production use, implement a proper expression evaluator "
            "such as py-expression-eval or a custom DSL parser. "
            "Do NOT use eval() for security reasons."
        )