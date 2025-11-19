"""Utility entrypoints and fallbacks for running Corona backend tooling."""

from .central_manager import CentralManager
from .dialogs import FileHandler
from .static_components import url
from .scene_service import SceneApplicationService, get_scene_service, set_scene_service
from .project_service import ProjectApplicationService, get_project_service, set_project_service
from .models import ProjectAsset, SceneDocument


__all__ = [
    "CentralManager",
    "FileHandler",
    "url",
    "SceneApplicationService",
    "ProjectApplicationService",
    "ProjectAsset",
    "SceneDocument",
    "get_scene_service",
    "set_scene_service",
    "get_project_service",
    "set_project_service",
]
