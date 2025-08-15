"""App endpoints registry for CIDS"""
from typing import Dict, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field, validator
import re
import json
from pathlib import Path

class Endpoint(BaseModel):
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|\\*)$")
    path: str = Field(..., min_length=1)
    desc: str = Field(..., min_length=1, max_length=500)
    
    @validator('path')
    def validate_path(cls, v):
        # Basic path validation - must start with /
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        # Allow wildcards
        if '*' in v and not re.match(r'^/[\w/\-{}]*\*?$', v):
            raise ValueError('Invalid wildcard usage in path')
        return v

class EndpointsUpdate(BaseModel):
    endpoints: List[Endpoint]
    version: Optional[str] = None

class AppEndpointsRegistry:
    """Manages endpoint definitions for registered apps"""
    
    def __init__(self, data_dir: str = "app_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.endpoints_file = self.data_dir / "app_endpoints.json"
        self.endpoints: Dict[str, Dict] = self._load_endpoints()
    
    def _load_endpoints(self) -> Dict[str, Dict]:
        """Load endpoints from persistent storage"""
        if self.endpoints_file.exists():
            try:
                with open(self.endpoints_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_endpoints(self):
        """Save endpoints to persistent storage"""
        with open(self.endpoints_file, 'w') as f:
            json.dump(self.endpoints, f, indent=2)
    
    def upsert_endpoints(self, app_client_id: str, update: EndpointsUpdate, updated_by: str) -> Dict:
        """Upsert endpoints for an app"""
        # Validate uniqueness within the app
        seen_endpoints = set()
        for endpoint in update.endpoints:
            key = f"{endpoint.method}:{endpoint.path}"
            if key in seen_endpoints:
                raise ValueError(f"Duplicate endpoint definition: {key}")
            seen_endpoints.add(key)
        
        # Check for conflicts with other apps (excluding wildcards)
        for other_app_id, other_data in self.endpoints.items():
            if other_app_id == app_client_id:
                continue
            
            for endpoint in update.endpoints:
                if '*' in endpoint.path or endpoint.method == '*':
                    continue  # Skip wildcard checks
                
                for other_endpoint in other_data.get('endpoints', []):
                    if ('*' not in other_endpoint['path'] and 
                        other_endpoint['method'] != '*' and
                        endpoint.method == other_endpoint['method'] and 
                        endpoint.path == other_endpoint['path']):
                        raise ValueError(
                            f"Endpoint {endpoint.method} {endpoint.path} conflicts with app {other_app_id}"
                        )
        
        # Generate version if not provided
        version = update.version or datetime.utcnow().strftime("%Y%m%d%H%M%S")
        
        # Store endpoints
        self.endpoints[app_client_id] = {
            'endpoints': [e.dict() for e in update.endpoints],
            'version': version,
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': updated_by
        }
        
        self._save_endpoints()
        
        return {
            'app_client_id': app_client_id,
            'endpoints_count': len(update.endpoints),
            'version': version,
            'updated_at': self.endpoints[app_client_id]['updated_at']
        }
    
    def get_app_endpoints(self, app_client_id: str) -> Optional[Dict]:
        """Get endpoints for a specific app"""
        return self.endpoints.get(app_client_id)
    
    def get_all_endpoints(self) -> Dict[str, Dict]:
        """Get all registered endpoints"""
        return self.endpoints
    
    def delete_app_endpoints(self, app_client_id: str) -> bool:
        """Delete endpoints for an app"""
        if app_client_id in self.endpoints:
            del self.endpoints[app_client_id]
            self._save_endpoints()
            return True
        return False
    
    def match_endpoint(self, method: str, path: str) -> List[Dict]:
        """Find which apps can handle a given endpoint"""
        matches = []
        
        for app_client_id, data in self.endpoints.items():
            for endpoint in data.get('endpoints', []):
                # Check method match
                if endpoint['method'] != '*' and endpoint['method'] != method:
                    continue
                
                # Check path match
                endpoint_path = endpoint['path']
                if '*' in endpoint_path:
                    # Convert wildcard to regex
                    pattern = endpoint_path.replace('*', '.*')
                    if re.match(f"^{pattern}$", path):
                        matches.append({
                            'app_client_id': app_client_id,
                            'endpoint': endpoint,
                            'version': data['version']
                        })
                elif endpoint_path == path:
                    matches.append({
                        'app_client_id': app_client_id,
                        'endpoint': endpoint,
                        'version': data['version']
                    })
        
        return matches