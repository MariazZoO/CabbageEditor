"""Utility entrypoints and fallbacks for running Corona backend tooling.

This module has been refactored to separate GUI dependencies from core business logic:
- Backend.utils.core: Core utilities (no GUI dependencies) - always available
- Backend.utils.gui: GUI utilities (requires PySide6) - optional

For backward compatibility, all exports are still available at the top level.
"""

# Core utilities (always available)
from .core import (
    SceneApplicationService,
    get_scene_service,
    set_scene_service,
    ProjectApplicationService,
    get_project_service,
    set_project_service,
    ProjectAsset,
    SceneDocument,
    configure_logging,
    get_logger,
    cleanup_blockly_files,
    clear_script_modules,
)

# GUI utilities (optional, may be None in server mode)
from .gui import (
    CentralManager,
    FileHandler,
    url,
    ScriptRunner,
    _GUI_AVAILABLE as GUI_AVAILABLE,
)

__all__ = [
    # Core utilities
    "SceneApplicationService",
    "get_scene_service",
    "set_scene_service",
    "ProjectApplicationService",
    "get_project_service",
    "set_project_service",
    "ProjectAsset",
    "SceneDocument",
    "configure_logging",
    "get_logger",
    "cleanup_blockly_files",
    "clear_script_modules",
    # GUI utilities (may be None)
    "CentralManager",
    "FileHandler",
    "url",
    "ScriptRunner",
    "GUI_AVAILABLE",
]
