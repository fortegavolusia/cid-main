"""
Placeholder API module to validate imports during migration.
"""

# Import modules we are migrating to ensure package paths are valid
from services.discovery import DiscoveryService  # noqa: F401
from services.permission_registry import PermissionRegistry  # noqa: F401
from schemas.discovery import DiscoveryResponse  # noqa: F401

