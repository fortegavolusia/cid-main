"""Resource Filter Policy v1 - Minimal policy compilation and management"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import hashlib
import hmac
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FilterClause(BaseModel):
    """Single filter clause - keys within are ANDed"""
    department: Optional[str] = Field(None, description="Match user's department")
    hierarchy: Optional[Dict[str, str]] = Field(None, description="Hierarchy filter config")
    ownership: Optional[Dict[str, str]] = Field(None, description="Ownership filter config")
    custom: Optional[Dict[str, str]] = Field(None, description="Custom attribute filter")

class ResourceScope(BaseModel):
    """Scope defining resource access"""
    resource_type: str
    actions: List[str]
    clauses: List[FilterClause] = Field([], description="OR between clauses")

class RolePolicy(BaseModel):
    """Complete role policy v1"""
    role: str
    version: int
    scopes: List[ResourceScope]

class PolicyCompiler:
    """Compiles role filter configurations into RolePolicy v1"""
    
    def compile_filters(self, role_name: str, version: int, 
                       resource_permissions: Dict[str, Any]) -> RolePolicy:
        """
        Compile resource permissions into policy format.
        Expects resource_permissions in format:
        {
            "work_order": {
                "actions": ["read", "update"],
                "filters": [
                    {"type": "department", "field": "department"},
                    {"type": "ownership", "field": "owner_id"}
                ]
            }
        }
        """
        scopes = []
        
        for resource_type, config in resource_permissions.items():
            clauses = []
            
            # Convert each filter to a clause
            for filter_def in config.get('filters', []):
                clause = self._build_clause(filter_def)
                if clause:
                    clauses.append(clause)
            
            scope = ResourceScope(
                resource_type=resource_type,
                actions=config.get('actions', []),
                clauses=clauses
            )
            scopes.append(scope)
        
        return RolePolicy(
            role=role_name,
            version=version,
            scopes=scopes
        )
    
    def _build_clause(self, filter_def: Dict) -> Optional[FilterClause]:
        """Build a single filter clause from filter definition"""
        filter_type = filter_def.get('type')
        
        if filter_type == 'department':
            return FilterClause(department="{user.department}")
        
        elif filter_type == 'hierarchy':
            return FilterClause(
                hierarchy={
                    "field": filter_def.get('field', 'created_by'),
                    "scope": filter_def.get('scope', 'subordinates')
                }
            )
        
        elif filter_type == 'ownership':
            return FilterClause(
                ownership={
                    "field": filter_def.get('field', 'owner_id'),
                    "equals": "{user.id}"
                }
            )
        
        elif filter_type == 'custom':
            return FilterClause(
                custom={
                    "field": filter_def.get('field'),
                    "equals": f"{{user.{filter_def.get('attribute', 'id')}}}"
                }
            )
        
        return None

class PolicyStore:
    """Stores and manages compiled policies"""
    
    def __init__(self, data_dir: str = "app_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.policies_dir = self.data_dir / "policies"
        self.policies_dir.mkdir(exist_ok=True)
        self.versions_file = self.data_dir / "policy_versions.json"
        self.versions = self._load_versions()
    
    def _load_versions(self) -> Dict:
        """Load policy versions"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading versions: {e}")
                return {}
        return {}
    
    def save_policy(self, app: str, role: str, policy: RolePolicy) -> int:
        """Save compiled policy and return new version"""
        key = f"{app}:{role}"
        
        # Increment version
        current_version = self.versions.get(key, 0)
        new_version = current_version + 1
        
        # Update policy version
        policy.version = new_version
        
        # Save policy file
        policy_file = self.policies_dir / f"{app}_{role}_v{new_version}.json"
        with open(policy_file, 'w') as f:
            json.dump(policy.dict(), f, indent=2)
        
        # Update versions
        self.versions[key] = new_version
        with open(self.versions_file, 'w') as f:
            json.dump(self.versions, f, indent=2)
        
        return new_version
    
    def get_policy(self, app: str, role: str, version: Optional[int] = None) -> Optional[RolePolicy]:
        """Get policy by app, role and optionally version"""
        key = f"{app}:{role}"
        
        if version is None:
            version = self.versions.get(key)
            if not version:
                return None
        
        policy_file = self.policies_dir / f"{app}_{role}_v{version}.json"
        if not policy_file.exists():
            return None
        
        try:
            with open(policy_file, 'r') as f:
                data = json.load(f)
                return RolePolicy(**data)
        except Exception as e:
            logger.error(f"Error loading policy: {e}")
            return None

class PolicyPusher:
    """Handles secure policy push to applications"""
    
    def __init__(self, app_secrets: Dict[str, str]):
        """Initialize with app client_id -> secret mapping"""
        self.app_secrets = app_secrets
    
    def generate_signature(self, app: str, payload: bytes) -> str:
        """Generate HMAC-SHA256 signature for payload"""
        secret = self.app_secrets.get(app)
        if not secret:
            raise ValueError(f"No secret configured for app: {app}")
        
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def verify_signature(self, app: str, payload: bytes, signature: str) -> bool:
        """Verify HMAC signature from app"""
        expected = self.generate_signature(app, payload)
        return hmac.compare_digest(expected, signature)

# Singleton instances
policy_compiler = PolicyCompiler()
policy_store = PolicyStore()