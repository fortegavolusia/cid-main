"""App endpoints registry for CIDS (migrated)"""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
import re
import json

from utils.paths import data_path


class Endpoint(BaseModel):
    method: str = Field(..., pattern=r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|\*)$")
    path: str = Field(..., min_length=1)
    desc: str = Field(..., min_length=1, max_length=500)

    @validator('path')
    def validate_path(cls, v):
        if not v.startswith('/'):
            raise ValueError('Path must start with /')
        if '*' in v and not re.match(r'^/[\w/\-{}]*\*?$', v):
            raise ValueError('Invalid wildcard usage in path')
        return v


class EndpointsUpdate(BaseModel):
    endpoints: List[Endpoint]
    version: Optional[str] = None


class AppEndpointsRegistry:
    """Manages endpoint definitions for registered apps"""

    def __init__(self):
        self.endpoints_file = data_path("app_endpoints.json")
        self.endpoints: Dict[str, Dict] = self._load_endpoints()

    def _load_endpoints(self) -> Dict[str, Dict]:
        if self.endpoints_file.exists():
            try:
                with open(self.endpoints_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_endpoints(self):
        self.endpoints_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.endpoints_file, 'w') as f:
            json.dump(self.endpoints, f, indent=2)

    def upsert_endpoints(self, app_client_id: str, endpoints: List[Dict], updated_by: str = "discovery-service") -> Dict:
        current = self.endpoints.get(app_client_id, {})
        current_endpoints = current.get('endpoints', [])
        existing_map = {f"{e['method']}:{e['path']}": e for e in current_endpoints if not e.get('discovered', False)}
        for endpoint in endpoints:
            key = f"{endpoint['method']}:{endpoint['path']}"
            existing_map[key] = endpoint
        merged_endpoints = list(existing_map.values())
        version = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self.endpoints[app_client_id] = {
            'endpoints': merged_endpoints,
            'version': version,
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': updated_by,
            'has_discovered': any(e.get('discovered', False) for e in merged_endpoints)
        }
        self._save_endpoints()
        return {
            'app_client_id': app_client_id,
            'endpoints_count': len(merged_endpoints),
            'discovered_count': sum(1 for e in merged_endpoints if e.get('discovered', False)),
            'version': version
        }

    def get_app_endpoints(self, app_client_id: str) -> Optional[Dict]:
        return self.endpoints.get(app_client_id)

    def get_all_endpoints(self) -> Dict[str, Dict]:
        return self.endpoints

    def delete_app_endpoints(self, app_client_id: str) -> bool:
        if app_client_id in self.endpoints:
            del self.endpoints[app_client_id]
            self._save_endpoints()
            return True
        return False

    def match_endpoint(self, method: str, path: str) -> List[Dict]:
        matches = []
        for app_client_id, data in self.endpoints.items():
            for endpoint in data.get('endpoints', []):
                if endpoint['method'] != '*' and endpoint['method'] != method:
                    continue
                endpoint_path = endpoint['path']
                if '*' in endpoint_path:
                    pattern = endpoint_path.replace('*', '.*')
                    if re.match(f"^{pattern}$", path):
                        matches.append({'app_client_id': app_client_id, 'endpoint': endpoint, 'version': data['version']})
                elif endpoint_path == path:
                    matches.append({'app_client_id': app_client_id, 'endpoint': endpoint, 'version': data['version']})
        return matches

