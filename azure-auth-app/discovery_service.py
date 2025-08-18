"""
Endpoint Discovery Service for CIDS

This service handles discovering and fetching endpoint metadata from registered applications.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import asyncio
import json
import logging
from pydantic import BaseModel, Field
from app_registration import registered_apps, save_data, load_data
from app_endpoints import AppEndpointsRegistry
from jwt_utils import JWTManager
import os

logger = logging.getLogger(__name__)

# Discovery metadata models
class EndpointMetadata(BaseModel):
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    path: str
    description: str
    required_permissions: Optional[List[str]] = []
    required_roles: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class DiscoveryResponse(BaseModel):
    version: str = "2.0"
    app_id: str
    endpoints: List[EndpointMetadata]
    last_updated: Optional[str] = None

class DiscoveryService:
    """Handles endpoint discovery from registered applications"""
    
    def __init__(self, jwt_manager: JWTManager, endpoints_registry: AppEndpointsRegistry):
        self.jwt_manager = jwt_manager
        self.endpoints_registry = endpoints_registry
        self.discovery_timeout = 10  # seconds
        self.max_retries = 3
        
    async def discover_endpoints(self, client_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Discover endpoints from a registered application
        
        Args:
            client_id: The application's client ID
            force: Force discovery even if recently checked
            
        Returns:
            Discovery result with status and discovered endpoints
        """
        load_data()  # Ensure latest data
        app = registered_apps.get(client_id)
        
        if not app:
            return {
                "status": "error",
                "error": "Application not found"
            }
            
        if not app.get("allow_discovery", False):
            return {
                "status": "error", 
                "error": "Application does not allow discovery"
            }
            
        discovery_endpoint = app.get("discovery_endpoint")
        if not discovery_endpoint:
            return {
                "status": "error",
                "error": "No discovery endpoint configured"
            }
            
        # Check if we should skip (rate limiting)
        if not force:
            last_discovery = app.get("last_discovery_at")
            if last_discovery:
                last_time = datetime.fromisoformat(last_discovery)
                if datetime.utcnow() - last_time < timedelta(minutes=5):
                    return {
                        "status": "skipped",
                        "message": "Recently discovered, skipping",
                        "last_discovery_at": last_discovery
                    }
        
        # Create service token for authentication
        service_token = self._create_service_token()
        
        # Attempt discovery
        try:
            endpoints = await self._fetch_endpoints(discovery_endpoint, service_token)
            
            # Validate response
            discovery_data = DiscoveryResponse(**endpoints)
            
            # Store discovered endpoints
            stored_count = await self._store_endpoints(client_id, discovery_data)
            
            # Update app discovery status
            app["last_discovery_at"] = datetime.utcnow().isoformat()
            app["discovery_status"] = "success"
            save_data()
            
            return {
                "status": "success",
                "endpoints_discovered": len(discovery_data.endpoints),
                "endpoints_stored": stored_count,
                "discovery_data": discovery_data.dict()
            }
            
        except httpx.TimeoutException:
            logger.error(f"Discovery timeout for {client_id}")
            app["discovery_status"] = "timeout"
            save_data()
            return {
                "status": "error",
                "error": "Discovery endpoint timeout"
            }
        except httpx.RequestError as e:
            logger.error(f"Discovery request error for {client_id}: {e}")
            app["discovery_status"] = "connection_error"
            save_data()
            return {
                "status": "error",
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Discovery error for {client_id}: {e}")
            app["discovery_status"] = "error"
            save_data()
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def discover_all_apps(self, force: bool = False) -> Dict[str, Any]:
        """Discover endpoints from all registered applications that allow discovery"""
        load_data()
        results = {}
        
        discovery_apps = [
            (client_id, app) for client_id, app in registered_apps.items()
            if app.get("allow_discovery", False) and app.get("discovery_endpoint")
        ]
        
        logger.info(f"Starting discovery for {len(discovery_apps)} applications")
        
        # Run discoveries in parallel with limited concurrency
        tasks = []
        for client_id, app in discovery_apps:
            task = self.discover_endpoints(client_id, force)
            tasks.append((client_id, task))
        
        # Execute with concurrency limit
        for client_id, task in tasks:
            result = await task
            results[client_id] = result
            
        return {
            "total_apps": len(discovery_apps),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _create_service_token(self) -> str:
        """Create a service token for CIDS to authenticate to apps"""
        claims = {
            'iss': 'internal-auth-service',
            'sub': 'cids-discovery-service',
            'aud': ['discovery-api'],
            'client_id': 'cids-discovery',
            'app_name': 'CIDS Discovery Service',
            'token_type': 'service',
            'permissions': ['discovery.read'],
            'token_version': '2.0'
        }
        return self.jwt_manager.create_token(claims, token_lifetime_minutes=5, token_type='access')
    
    async def _fetch_endpoints(self, discovery_url: str, token: str) -> Dict:
        """Fetch endpoints from discovery URL"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CIDS-Discovery/1.0"
        }
        
        async with httpx.AsyncClient(timeout=self.discovery_timeout, verify=False) as client:
            response = await client.get(discovery_url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _store_endpoints(self, client_id: str, discovery_data: DiscoveryResponse) -> int:
        """Store discovered endpoints in the registry"""
        stored = 0
        
        # Convert discovered endpoints to registry format
        endpoints_to_store = []
        for endpoint in discovery_data.endpoints:
            endpoints_to_store.append({
                "method": endpoint.method,
                "path": endpoint.path,
                "description": endpoint.description,
                "discovered": True,
                "discovered_at": datetime.utcnow().isoformat(),
                "required_permissions": endpoint.required_permissions,
                "required_roles": endpoint.required_roles,
                "tags": endpoint.tags
            })
        
        # Store in registry (this will handle deduplication)
        try:
            self.endpoints_registry.upsert_endpoints(client_id, endpoints_to_store)
            stored = len(endpoints_to_store)
        except Exception as e:
            logger.error(f"Failed to store endpoints for {client_id}: {e}")
            
        return stored

    def get_discovery_status(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Get discovery status for one or all apps"""
        load_data()
        
        if client_id:
            app = registered_apps.get(client_id)
            if not app:
                return {"error": "Application not found"}
                
            return {
                "client_id": client_id,
                "app_name": app.get("name"),
                "allow_discovery": app.get("allow_discovery", False),
                "discovery_endpoint": app.get("discovery_endpoint"),
                "last_discovery_at": app.get("last_discovery_at"),
                "discovery_status": app.get("discovery_status"),
                "endpoints_count": len(self.endpoints_registry.get_app_endpoints(client_id))
            }
        else:
            # Return status for all apps
            statuses = []
            for cid, app in registered_apps.items():
                if app.get("allow_discovery", False):
                    statuses.append({
                        "client_id": cid,
                        "app_name": app.get("name"),
                        "last_discovery_at": app.get("last_discovery_at"),
                        "discovery_status": app.get("discovery_status"),
                        "endpoints_count": len(self.endpoints_registry.get_app_endpoints(cid))
                    })
            
            return {
                "total_discoverable_apps": len(statuses),
                "apps": statuses
            }