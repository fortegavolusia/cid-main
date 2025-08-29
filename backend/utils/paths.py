from pathlib import Path
import os

# Base directories
BACKEND_ROOT = Path(__file__).resolve().parents[1]
INFRA_DIR = BACKEND_ROOT / "infra"
DATA_DIR = INFRA_DIR / "data" / "app_data"
CONFIG_DIR = INFRA_DIR / "config"
LOGS_DIR = INFRA_DIR / "logs"
API_DIR = BACKEND_ROOT / "api"


def data_path(*parts: str) -> Path:
    """Resolve a path under backend/infra/data/app_data"""
    return (DATA_DIR.joinpath(*parts)).resolve()


def config_path(*parts: str) -> Path:
    """Resolve a path under backend/infra/config"""
    return (CONFIG_DIR.joinpath(*parts)).resolve()


def logs_path(*parts: str) -> Path:
    """Resolve a path under backend/infra/logs"""
    return (LOGS_DIR.joinpath(*parts)).resolve()


def api_templates_path() -> Path:
    """Default Jinja templates directory for API layer"""
    return (API_DIR / "templates").resolve()


def ensure_dirs():
    """Create expected infra directories if missing (safe no-op if exist)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

