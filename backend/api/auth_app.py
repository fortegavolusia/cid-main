"""
Placeholder API module to validate imports during migration.
"""

# Import modules we are migrating to ensure package paths are valid
from backend.services.discovery import DiscoveryService  # noqa: F401
from backend.services.permission_registry import PermissionRegistry  # noqa: F401
from backend.schemas.discovery import DiscoveryResponse  # noqa: F401

