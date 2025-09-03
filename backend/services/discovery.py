"""
Enhanced Discovery Service with robust error handling, retry logic, and progress tracking
"""
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
import httpx
import asyncio
import json
import logging
import time
import random
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from backend.schemas.discovery import (
    DiscoveryResponse, EndpointMetadata, FieldMetadata,
    PermissionMetadata, DiscoveredPermissions,
    generate_permission_key, extract_resource_from_path,
    extract_action_from_method, FieldType
)
from backend.utils.paths import data_path
from backend.services.jwt import JWTManager
from backend.services.endpoints import AppEndpointsRegistry
from backend.services.permission_registry import PermissionRegistry
from backend.services.app_registration import registered_apps, save_data

logger = logging.getLogger(__name__)

PERMISSIONS_FILE = data_path("discovered_permissions.json")
FIELD_METADATA_FILE = data_path("field_metadata.json")
DISCOVERY_HISTORY_FILE = data_path("discovery_history.json")


class DiscoveryErrorType(Enum):
    """Classification of discovery errors"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    VALIDATION_ERROR = "validation_error"
    CONFIGURATION_ERROR = "configuration_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class DiscoveryStatus(Enum):
    """Discovery operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class DiscoveryConfig:
    """Configuration for discovery operations"""
    timeout_seconds: int = 30
    connect_timeout_seconds: int = 10
    max_retries: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    retry_exponential_base: float = 2.0
    enable_health_check: bool = True
    health_check_timeout: int = 5
    validate_schema: bool = True
    cache_duration_minutes: int = 60


@dataclass
class DiscoveryAttempt:
    """Record of a single discovery attempt"""
    timestamp: datetime
    success: bool
    error_type: Optional[DiscoveryErrorType] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    endpoints_found: int = 0
    permissions_generated: int = 0


@dataclass
class DiscoveryHistory:
    """History of discovery attempts for an app"""
    app_id: str
    app_name: str
    discovery_endpoint: str
    attempts: List[DiscoveryAttempt]
    last_successful_discovery: Optional[datetime] = None
    total_attempts: int = 0
    success_rate: float = 0.0


@dataclass
class DiscoveryProgress:
    """Progress tracking for discovery operations"""
    app_id: str
    status: DiscoveryStatus
    current_step: str
    progress_percentage: int = 0
    start_time: datetime = None
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class DiscoveryService:
    """Enhanced field-level discovery service with robust error handling and retry logic"""

    def __init__(self, jwt_manager: JWTManager, endpoints_registry: Optional[AppEndpointsRegistry] = None,
                 permission_registry: Optional[PermissionRegistry] = None, config: Optional[DiscoveryConfig] = None):
        self.jwt_manager = jwt_manager
        self.endpoints_registry = endpoints_registry
        self.permission_registry = permission_registry or PermissionRegistry()
        self.config = config or DiscoveryConfig()
        self.permissions_cache: Dict[str, DiscoveredPermissions] = {}
        self.discovery_history: Dict[str, DiscoveryHistory] = {}
        self.active_discoveries: Dict[str, DiscoveryProgress] = {}
        self.progress_callbacks: Dict[str, List[Callable[[DiscoveryProgress], None]]] = {}

        self._load_permissions()
        self._load_discovery_history()

    def _load_permissions(self):
        """Load cached permissions from disk"""
        try:
            if PERMISSIONS_FILE.exists():
                with open(PERMISSIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for app_id, perm_data in data.items():
                        self.permissions_cache[app_id] = DiscoveredPermissions(**perm_data)
                logger.info(f"Loaded permissions for {len(self.permissions_cache)} apps")
        except Exception as e:
            logger.error(f"Error loading permissions: {e}")
            self.permissions_cache = {}

    def _save_permissions(self):
        """Save permissions cache to disk"""
        try:
            PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {app_id: perms.dict() for app_id, perms in self.permissions_cache.items()}
            with open(PERMISSIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved permissions for {len(self.permissions_cache)} apps")
        except Exception as e:
            logger.error(f"Error saving permissions: {e}")

    def _load_discovery_history(self):
        """Load discovery history from disk"""
        try:
            if DISCOVERY_HISTORY_FILE.exists():
                with open(DISCOVERY_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    for app_id, history_data in data.items():
                        # Convert datetime strings back to datetime objects
                        attempts = []
                        for attempt_data in history_data.get('attempts', []):
                            attempt_data['timestamp'] = datetime.fromisoformat(attempt_data['timestamp'])
                            if attempt_data.get('error_type'):
                                attempt_data['error_type'] = DiscoveryErrorType(attempt_data['error_type'])
                            attempts.append(DiscoveryAttempt(**attempt_data))

                        history_data['attempts'] = attempts
                        if history_data.get('last_successful_discovery'):
                            history_data['last_successful_discovery'] = datetime.fromisoformat(
                                history_data['last_successful_discovery']
                            )

                        self.discovery_history[app_id] = DiscoveryHistory(**history_data)
                logger.info(f"Loaded discovery history for {len(self.discovery_history)} apps")
        except Exception as e:
            logger.error(f"Error loading discovery history: {e}")
            self.discovery_history = {}

    def _save_discovery_history(self):
        """Save discovery history to disk"""
        try:
            DISCOVERY_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for app_id, history in self.discovery_history.items():
                history_dict = asdict(history)
                # Convert datetime objects to strings for JSON serialization
                for attempt in history_dict['attempts']:
                    attempt['timestamp'] = attempt['timestamp'].isoformat()
                    if attempt['error_type']:
                        attempt['error_type'] = attempt['error_type'].value

                if history_dict['last_successful_discovery']:
                    history_dict['last_successful_discovery'] = history_dict['last_successful_discovery'].isoformat()

                data[app_id] = history_dict

            with open(DISCOVERY_HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved discovery history for {len(self.discovery_history)} apps")
        except Exception as e:
            logger.error(f"Error saving discovery history: {e}")

    def register_progress_callback(self, app_id: str, callback: Callable[[DiscoveryProgress], None]):
        """Register a callback to receive progress updates for an app's discovery"""
        if app_id not in self.progress_callbacks:
            self.progress_callbacks[app_id] = []
        self.progress_callbacks[app_id].append(callback)

    def _update_progress(self, app_id: str, status: DiscoveryStatus, step: str,
                        progress: int = 0, error_message: str = None):
        """Update and broadcast discovery progress"""
        if app_id not in self.active_discoveries:
            self.active_discoveries[app_id] = DiscoveryProgress(
                app_id=app_id,
                status=status,
                current_step=step,
                start_time=datetime.utcnow()
            )

        progress_obj = self.active_discoveries[app_id]
        progress_obj.status = status
        progress_obj.current_step = step
        progress_obj.progress_percentage = progress
        progress_obj.error_message = error_message

        # Estimate completion time based on progress
        if progress > 0 and progress_obj.start_time:
            elapsed = datetime.utcnow() - progress_obj.start_time
            total_estimated = elapsed * (100 / progress)
            progress_obj.estimated_completion = progress_obj.start_time + total_estimated

        # Notify callbacks
        for callback in self.progress_callbacks.get(app_id, []):
            try:
                callback(progress_obj)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def _classify_error(self, error: Exception) -> DiscoveryErrorType:
        """Classify an error into a specific type"""
        if isinstance(error, httpx.ConnectError):
            return DiscoveryErrorType.NETWORK_ERROR
        elif isinstance(error, httpx.TimeoutException):
            return DiscoveryErrorType.TIMEOUT_ERROR
        elif isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code in [401, 403]:
                return DiscoveryErrorType.AUTHENTICATION_ERROR
            elif error.response.status_code >= 500:
                return DiscoveryErrorType.SERVER_ERROR
            else:
                return DiscoveryErrorType.VALIDATION_ERROR
        elif isinstance(error, (ValueError, KeyError, TypeError)):
            return DiscoveryErrorType.VALIDATION_ERROR
        else:
            return DiscoveryErrorType.UNKNOWN_ERROR

    async def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff retry logic"""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_type = self._classify_error(e)

                # Don't retry certain types of errors
                if error_type in [DiscoveryErrorType.AUTHENTICATION_ERROR,
                                DiscoveryErrorType.CONFIGURATION_ERROR]:
                    raise e

                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.base_retry_delay * (self.config.retry_exponential_base ** attempt),
                        self.config.max_retry_delay
                    )
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    logger.warning(f"Discovery attempt {attempt + 1} failed: {e}. Retrying in {total_delay:.2f}s")
                    await asyncio.sleep(total_delay)
                else:
                    logger.error(f"All {self.config.max_retries + 1} discovery attempts failed")
                    raise e

        raise last_exception

    async def discover_with_fields(self, client_id: str, force: bool = False) -> Dict[str, Any]:
        """Enhanced discovery with progress tracking, retry logic, and comprehensive error handling"""
        start_time = datetime.utcnow()

        # Initialize progress tracking
        self._update_progress(client_id, DiscoveryStatus.PENDING, "Validating configuration", 0)

        try:
            # Load app config
            app = registered_apps.get(client_id)
            if not app:
                error_msg = "Application not found"
                self._update_progress(client_id, DiscoveryStatus.FAILED, "Configuration validation failed", 0, error_msg)
                return {"status": "error", "error": error_msg, "error_type": "configuration_error"}

            if not app.get("allow_discovery", False):
                error_msg = "Application does not allow discovery"
                self._update_progress(client_id, DiscoveryStatus.FAILED, "Configuration validation failed", 0, error_msg)
                return {"status": "error", "error": error_msg, "error_type": "configuration_error"}

            discovery_endpoint = app.get("discovery_endpoint")
            if not discovery_endpoint:
                error_msg = "No discovery endpoint configured"
                self._update_progress(client_id, DiscoveryStatus.FAILED, "Configuration validation failed", 0, error_msg)
                return {"status": "error", "error": error_msg, "error_type": "configuration_error"}

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Checking cache", 10)

            # Check cache unless forced
            if not force and client_id in self.permissions_cache:
                cached = self.permissions_cache[client_id]
                cache_age = datetime.utcnow() - cached.last_discovered
                if cache_age < timedelta(minutes=self.config.cache_duration_minutes):
                    last = app.get("last_discovery_at") or cached.last_discovered.isoformat()
                    self._update_progress(client_id, DiscoveryStatus.CACHED, "Using cached data", 100)
                    return {
                        "status": "cached",
                        "message": f"Using cached discovery data (age: {cache_age})",
                        "permissions_count": cached.total_count,
                        "last_discovery_at": last,
                        "cache_age_minutes": int(cache_age.total_seconds() / 60)
                    }

            # Perform health check if enabled
            if self.config.enable_health_check:
                self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Performing health check", 20)
                health_check_result = await self._perform_health_check(discovery_endpoint)
                if not health_check_result["healthy"]:
                    error_msg = f"Health check failed: {health_check_result['error']}"
                    self._update_progress(client_id, DiscoveryStatus.FAILED, "Health check failed", 20, error_msg)
                    self._record_discovery_attempt(client_id, app, start_time, False,
                                                 DiscoveryErrorType.NETWORK_ERROR, error_msg)
                    return {"status": "error", "error": error_msg, "error_type": "network_error"}

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Creating service token", 30)
            service_token = self._create_service_token()

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Fetching discovery data", 40)

            # Use retry logic for the discovery fetch
            discovery_json = await self._retry_with_backoff(
                self._fetch_enhanced_discovery, discovery_endpoint, service_token
            )

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Validating discovery response", 60)

            # Validate against schema
            if self.config.validate_schema:
                discovery_data = await self._validate_discovery_response(discovery_json)
            else:
                discovery_data = DiscoveryResponse(**discovery_json)

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Generating permissions", 70)

            # Generate permissions
            permissions = self._generate_permissions(client_id, discovery_data)
            self.permissions_cache[client_id] = permissions

            # Register with central permission registry
            try:
                self.permission_registry.register_permissions(client_id, permissions.permissions)
            except Exception as e:
                logger.warning(f"Failed to register permissions in registry: {e}")

            self._save_permissions()

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Updating app status", 80)

            # Update app discovery status
            app["last_discovery_at"] = datetime.utcnow().isoformat()
            app["discovery_status"] = "success"
            app["discovery_version"] = getattr(discovery_data, 'discovery_version', "2.0")
            save_data()

            self._update_progress(client_id, DiscoveryStatus.IN_PROGRESS, "Storing metadata", 90)

            # Store field metadata and endpoints
            await self._store_field_metadata(client_id, discovery_data)

            endpoints_stored = 0
            if self.endpoints_registry and discovery_data.endpoints:
                endpoints_stored = await self._store_endpoints(client_id, discovery_data)

            # Record successful attempt
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._record_discovery_attempt(client_id, app, start_time, True, None, None,
                                         response_time, len(discovery_data.endpoints or []),
                                         permissions.total_count)

            self._update_progress(client_id, DiscoveryStatus.SUCCESS, "Discovery completed", 100)

            return {
                "status": "success",
                "endpoints_discovered": len(discovery_data.endpoints or []),
                "endpoints_stored": endpoints_stored,
                "services_discovered": len(discovery_data.services or []),
                "permissions_generated": permissions.total_count,
                "sensitive_permissions": permissions.sensitive_count,
                "sample_permissions": list(permissions.permissions.keys())[:10],
                "response_time_ms": response_time,
                "discovery_version": getattr(discovery_data, 'discovery_version', "2.0")
            }
        except Exception as e:
            # Comprehensive error handling with classification
            error_type = self._classify_error(e)
            error_msg = str(e)
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Update app status based on error type
            if error_type == DiscoveryErrorType.NETWORK_ERROR:
                app["discovery_status"] = "connection_error"
            elif error_type == DiscoveryErrorType.TIMEOUT_ERROR:
                app["discovery_status"] = "timeout"
            elif error_type == DiscoveryErrorType.AUTHENTICATION_ERROR:
                app["discovery_status"] = "auth_error"
            elif error_type == DiscoveryErrorType.VALIDATION_ERROR:
                app["discovery_status"] = "validation_error"
            else:
                app["discovery_status"] = "error"

            save_data()

            # Record failed attempt
            self._record_discovery_attempt(client_id, app, start_time, False, error_type, error_msg, response_time)

            # Update progress
            self._update_progress(client_id, DiscoveryStatus.FAILED, f"Discovery failed: {error_type.value}", 0, error_msg)

            logger.error(f"Discovery failed for {client_id}: {error_type.value} - {error_msg}")

            return {
                "status": "error",
                "error": error_msg,
                "error_type": error_type.value,
                "discovery_endpoint": discovery_endpoint,
                "response_time_ms": response_time
            }
        finally:
            # Clean up active discovery tracking
            if client_id in self.active_discoveries:
                del self.active_discoveries[client_id]

    def _create_service_token(self) -> str:
        """Create a service token for discovery authentication"""
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

    async def _perform_health_check(self, discovery_endpoint: str) -> Dict[str, Any]:
        """Perform a basic health check on the discovery endpoint"""
        try:
            # Simple HEAD request to check if endpoint is reachable
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.health_check_timeout),
                verify=False
            ) as client:
                response = await client.head(discovery_endpoint)
                return {
                    "healthy": response.status_code < 500,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "error_type": self._classify_error(e).value
            }

    async def _validate_discovery_response(self, discovery_json: Dict) -> DiscoveryResponse:
        """Validate discovery response with detailed error reporting"""
        try:
            # Basic structure validation
            if not isinstance(discovery_json, dict):
                raise ValueError("Discovery response must be a JSON object")

            required_fields = ['app_id', 'app_name']
            missing_fields = [field for field in required_fields if field not in discovery_json]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            # Validate endpoints or services are present
            has_endpoints = discovery_json.get('endpoints') is not None
            has_services = discovery_json.get('services') is not None

            if not has_endpoints and not has_services:
                raise ValueError("Discovery response must contain either 'endpoints' or 'services'")

            # Create and validate the response object
            discovery_data = DiscoveryResponse(**discovery_json)

            # Additional validation
            if discovery_data.endpoints:
                for i, endpoint in enumerate(discovery_data.endpoints):
                    if not endpoint.path or not endpoint.method:
                        raise ValueError(f"Endpoint {i} missing required path or method")

            if discovery_data.services:
                for i, service in enumerate(discovery_data.services):
                    if not service.name:
                        raise ValueError(f"Service {i} missing required name")

            return discovery_data

        except Exception as e:
            logger.error(f"Discovery response validation failed: {e}")
            raise ValueError(f"Invalid discovery response: {e}")

    def _record_discovery_attempt(self, client_id: str, app: Dict, start_time: datetime,
                                success: bool, error_type: Optional[DiscoveryErrorType] = None,
                                error_message: Optional[str] = None, response_time_ms: Optional[int] = None,
                                endpoints_found: int = 0, permissions_generated: int = 0):
        """Record a discovery attempt in the history"""
        attempt = DiscoveryAttempt(
            timestamp=start_time,
            success=success,
            error_type=error_type,
            error_message=error_message,
            response_time_ms=response_time_ms,
            endpoints_found=endpoints_found,
            permissions_generated=permissions_generated
        )

        app_name = app.get('app_name', 'Unknown App')
        discovery_endpoint = app.get('discovery_endpoint', '')

        if client_id not in self.discovery_history:
            self.discovery_history[client_id] = DiscoveryHistory(
                app_id=client_id,
                app_name=app_name,
                discovery_endpoint=discovery_endpoint,
                attempts=[]
            )

        history = self.discovery_history[client_id]
        history.attempts.append(attempt)
        history.total_attempts += 1

        if success:
            history.last_successful_discovery = start_time

        # Calculate success rate
        successful_attempts = sum(1 for a in history.attempts if a.success)
        history.success_rate = successful_attempts / len(history.attempts) if history.attempts else 0.0

        # Keep only last 100 attempts to prevent unbounded growth
        if len(history.attempts) > 100:
            history.attempts = history.attempts[-100:]

        self._save_discovery_history()

    async def _fetch_enhanced_discovery(self, discovery_url: str, token: str) -> Dict:
        """Fetch discovery data from the app's discovery endpoint"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CIDS-Discovery/2.0",
            "X-Discovery-Version": "2.0"
        }
        url = discovery_url if '?' in discovery_url else f"{discovery_url}?version=2.0"

        timeout = httpx.Timeout(
            self.config.timeout_seconds,
            connect=self.config.connect_timeout_seconds
        )

        async with httpx.AsyncClient(
            timeout=timeout,
            verify=False,
            follow_redirects=True
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _generate_permissions(self, app_id: str, discovery: DiscoveryResponse) -> DiscoveredPermissions:
        permissions: Dict[str, PermissionMetadata] = {}
        if discovery.endpoints:
            for endpoint in discovery.endpoints:
                self._process_endpoint_permissions(app_id, endpoint, permissions)
        if discovery.services:
            for service in discovery.services:
                for endpoint in service.endpoints:
                    self._process_endpoint_permissions(app_id, endpoint, permissions, service_prefix=service.name)
        sensitive_count = sum(1 for p in permissions.values() if p.sensitive or p.pii or p.phi)
        return DiscoveredPermissions(
            app_id=app_id,
            permissions=permissions,
            total_count=len(permissions),
            sensitive_count=sensitive_count,
            last_discovered=datetime.utcnow(),
            discovery_version="2.0",
        )

    def _process_endpoint_permissions(self, app_id: str, endpoint: EndpointMetadata, permissions: Dict[str, PermissionMetadata], service_prefix: Optional[str] = None):
        resource = extract_resource_from_path(endpoint.path)
        if service_prefix:
            resource = f"{service_prefix}_{resource}"
        is_collection = not endpoint.path.rstrip('/').endswith('}')
        action = extract_action_from_method(endpoint.method, is_collection)
        if endpoint.response_fields and endpoint.method == "GET":
            self._process_fields(app_id, resource, "read", endpoint.response_fields, endpoint.operation_id, permissions)
        if endpoint.request_fields and endpoint.method in ["POST", "PUT", "PATCH"]:
            self._process_fields(app_id, resource, "write", endpoint.request_fields, endpoint.operation_id, permissions)
        endpoint_perm_key = generate_permission_key(app_id, resource, action, "*")
        if endpoint_perm_key not in permissions:
            permissions[endpoint_perm_key] = PermissionMetadata(
                permission_key=endpoint_perm_key,
                resource=resource,
                action=action,
                field_path="*",
                description=f"{action.capitalize()} all fields for {resource}",
                endpoint_id=endpoint.operation_id,
            )

    def _process_fields(self, app_id: str, resource: str, action: str, fields: Dict[str, FieldMetadata], endpoint_id: str, permissions: Dict[str, PermissionMetadata], parent_path: str = ""):
        for field_name, field_meta in fields.items():
            field_path = f"{parent_path}.{field_name}" if parent_path else field_name
            perm_key = generate_permission_key(app_id, resource, action, field_path)
            permissions[perm_key] = PermissionMetadata(
                permission_key=perm_key,
                resource=resource,
                action=action,
                field_path=field_path,
                description=field_meta.description or f"{action.capitalize()} {field_path}",
                sensitive=field_meta.sensitive,
                pii=field_meta.pii,
                phi=field_meta.phi,
                endpoint_id=endpoint_id,
            )
            if field_meta.type == FieldType.OBJECT and field_meta.fields:
                self._process_fields(app_id, resource, action, field_meta.fields, endpoint_id, permissions, field_path)
            elif field_meta.type == FieldType.ARRAY and field_meta.items:
                if field_meta.items.type == FieldType.OBJECT and field_meta.items.fields:
                    self._process_fields(app_id, resource, action, field_meta.items.fields, endpoint_id, permissions, f"{field_path}[]")

    async def _store_field_metadata(self, app_id: str, discovery: DiscoveryResponse):
        try:
            metadata = {}
            if FIELD_METADATA_FILE.exists():
                with open(FIELD_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
            metadata[app_id] = {
                "app_name": discovery.app_name,
                "last_updated": discovery.last_updated.isoformat(),
                "endpoints": discovery.dict().get("endpoints", []),
                "services": discovery.dict().get("services", []),
            }
            FIELD_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FIELD_METADATA_FILE, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error storing field metadata: {e}")

    # Exposed helper methods for UI/administration
    def get_app_permissions(self, app_id: str) -> Optional[DiscoveredPermissions]:
        return self.permissions_cache.get(app_id)

    def search_permissions(self, app_id: Optional[str] = None, resource: Optional[str] = None, action: Optional[str] = None, sensitive_only: bool = False):
        """Return a list of PermissionMetadata objects (legacy-compatible)."""
        # permission_registry.search_permissions returns List[Tuple[app_id, PermissionMetadata]]
        results = self.permission_registry.search_permissions(app_id, resource, action, None, sensitive_only)
        return [perm for (_aid, perm) in results]

    def get_permission_tree(self, app_id: str):
        """Return legacy tree shape: resource -> action -> {fields: [], has_wildcard: bool, sensitive_count: int}"""
        tree: Dict[str, Dict[str, Dict[str, Any]]] = {}
        perms = self.permission_registry.get_app_permissions(app_id).values()
        for perm in perms:
            res = perm.resource
            act = perm.action
            if res not in tree:
                tree[res] = {}
            if act not in tree[res]:
                tree[res][act] = {"fields": [], "has_wildcard": False, "sensitive_count": 0}
            if perm.field_path == "*":
                tree[res][act]["has_wildcard"] = True
            else:
                field_info = {
                    "path": perm.field_path,
                    "permission_key": perm.permission_key,
                    "description": perm.description,
                    "sensitive": getattr(perm, "sensitive", False),
                    "pii": getattr(perm, "pii", False),
                    "phi": getattr(perm, "phi", False),
                }
                tree[res][act]["fields"].append(field_info)
                if field_info["sensitive"] or field_info["pii"] or field_info["phi"]:
                    tree[res][act]["sensitive_count"] += 1
        return tree

    async def _store_endpoints(self, client_id: str, discovery_data: DiscoveryResponse) -> int:
        if not self.endpoints_registry:
            return 0
        stored = 0
        endpoints_to_store = []
        if discovery_data.endpoints:
            for endpoint in discovery_data.endpoints:
                endpoints_to_store.append({
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "description": endpoint.description,
                    "discovered": True,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "required_permissions": getattr(endpoint, 'required_permissions', []),
                    "required_roles": getattr(endpoint, 'required_roles', []),
                    "tags": getattr(endpoint, 'tags', []),
                })
        try:
            if endpoints_to_store:
                self.endpoints_registry.upsert_endpoints(client_id, endpoints_to_store)
                stored = len(endpoints_to_store)
        except Exception:
            pass
        return stored

    # Enhanced API methods for batch operations and history

    async def batch_discover(self, client_ids: List[str], force: bool = False) -> Dict[str, Any]:
        """Run discovery on multiple apps simultaneously"""
        results = {}
        tasks = []

        for client_id in client_ids:
            task = asyncio.create_task(self.discover_with_fields(client_id, force))
            tasks.append((client_id, task))

        for client_id, task in tasks:
            try:
                result = await task
                results[client_id] = result
            except Exception as e:
                results[client_id] = {
                    "status": "error",
                    "error": str(e),
                    "error_type": "batch_error"
                }

        # Summary statistics
        successful = sum(1 for r in results.values() if r.get("status") == "success")
        failed = sum(1 for r in results.values() if r.get("status") == "error")
        cached = sum(1 for r in results.values() if r.get("status") == "cached")

        return {
            "batch_results": results,
            "summary": {
                "total": len(client_ids),
                "successful": successful,
                "failed": failed,
                "cached": cached,
                "success_rate": successful / len(client_ids) if client_ids else 0
            }
        }

    def get_discovery_history(self, client_id: str) -> Optional[DiscoveryHistory]:
        """Get discovery history for a specific app"""
        return self.discovery_history.get(client_id)

    def get_all_discovery_history(self) -> Dict[str, DiscoveryHistory]:
        """Get discovery history for all apps"""
        return self.discovery_history.copy()

    def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get overall discovery statistics"""
        if not self.discovery_history:
            return {
                "total_apps": 0,
                "total_attempts": 0,
                "overall_success_rate": 0.0,
                "apps_with_recent_success": 0,
                "apps_with_failures": 0
            }

        total_attempts = sum(h.total_attempts for h in self.discovery_history.values())
        successful_attempts = sum(
            sum(1 for a in h.attempts if a.success)
            for h in self.discovery_history.values()
        )

        recent_threshold = datetime.utcnow() - timedelta(hours=24)
        apps_with_recent_success = sum(
            1 for h in self.discovery_history.values()
            if h.last_successful_discovery and h.last_successful_discovery > recent_threshold
        )

        apps_with_failures = sum(
            1 for h in self.discovery_history.values()
            if any(not a.success for a in h.attempts[-10:])  # Recent failures
        )

        return {
            "total_apps": len(self.discovery_history),
            "total_attempts": total_attempts,
            "overall_success_rate": successful_attempts / total_attempts if total_attempts > 0 else 0.0,
            "apps_with_recent_success": apps_with_recent_success,
            "apps_with_failures": apps_with_failures,
            "average_response_time_ms": self._calculate_average_response_time()
        }

    def _calculate_average_response_time(self) -> float:
        """Calculate average response time across all successful attempts"""
        response_times = []
        for history in self.discovery_history.values():
            for attempt in history.attempts:
                if attempt.success and attempt.response_time_ms:
                    response_times.append(attempt.response_time_ms)

        return sum(response_times) / len(response_times) if response_times else 0.0

    def get_active_discoveries(self) -> Dict[str, DiscoveryProgress]:
        """Get currently active discovery operations"""
        return self.active_discoveries.copy()

    def update_config(self, new_config: DiscoveryConfig):
        """Update discovery configuration"""
        self.config = new_config
        logger.info(f"Discovery configuration updated: {asdict(new_config)}")

    def test_discovery_endpoint(self, discovery_endpoint: str) -> Dict[str, Any]:
        """Test a discovery endpoint without running full discovery"""
        async def _test():
            # Health check
            health_result = await self._perform_health_check(discovery_endpoint)
            if not health_result["healthy"]:
                return {
                    "status": "failed",
                    "stage": "health_check",
                    "error": health_result.get("error", "Health check failed"),
                    "details": health_result
                }

            # Try to fetch discovery data
            try:
                service_token = self._create_service_token()
                discovery_json = await self._fetch_enhanced_discovery(discovery_endpoint, service_token)

                # Validate response
                if self.config.validate_schema:
                    discovery_data = await self._validate_discovery_response(discovery_json)
                else:
                    discovery_data = DiscoveryResponse(**discovery_json)

                return {
                    "status": "success",
                    "endpoints_found": len(discovery_data.endpoints or []),
                    "services_found": len(discovery_data.services or []),
                    "app_name": discovery_data.app_name,
                    "discovery_version": getattr(discovery_data, 'discovery_version', "2.0"),
                    "health_check": health_result
                }

            except Exception as e:
                error_type = self._classify_error(e)
                return {
                    "status": "failed",
                    "stage": "discovery_fetch",
                    "error": str(e),
                    "error_type": error_type.value,
                    "health_check": health_result
                }

        # Run the test
        return asyncio.run(_test())

