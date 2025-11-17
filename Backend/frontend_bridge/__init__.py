"""Qt WebChannel service adapters that bridge UI signals to application services."""

from importlib import import_module
from typing import Any, TYPE_CHECKING

_ATTR_MAP = {
    # map exported attribute name -> (module_path, attribute_name)
    "AIService": ("Backend.frontend_bridge.ai_bridge", "AIService"),
    "ImageGenerationService": ("Backend.frontend_bridge.image_generation_bridge", "ImageGenerationService"),
    "AppService": ("Backend.frontend_bridge.app_bridge", "AppService"),
    "ProjectService": ("Backend.frontend_bridge.project_bridge", "ProjectService"),
    "SceneService": ("Backend.frontend_bridge.scene_bridge", "SceneService"),
    "ScriptingService": ("Backend.frontend_bridge.scripting_bridge", "ScriptingService"),
    "setup_webchannel_for_view": ("Backend.frontend_bridge.webchannel", "setup_webchannel_for_view"),
    "teardown_webchannel_for_view": ("Backend.frontend_bridge.webchannel", "teardown_webchannel_for_view"),
}

__all__ = list(_ATTR_MAP.keys())

if TYPE_CHECKING:
    # 仅供类型检查器/IDE 使用，运行时不执行这些导入
    from Backend.frontend_bridge.ai_bridge import AIService  # type: ignore
    from Backend.frontend_bridge.image_generation_bridge import ImageGenerationService  # type: ignore
    from Backend.frontend_bridge.app_bridge import AppService  # type: ignore
    from Backend.frontend_bridge.project_bridge import ProjectService  # type: ignore
    from Backend.frontend_bridge.scene_bridge import SceneService  # type: ignore
    from Backend.frontend_bridge.scripting_bridge import ScriptingService  # type: ignore
    from Backend.frontend_bridge.webchannel import setup_webchannel_for_view, \
        teardown_webchannel_for_view  # type: ignore


def __getattr__(name: str) -> Any:
    if name not in _ATTR_MAP:
        raise AttributeError(f"module 'Backend.frontend_bridge' has no attribute '{name}'")
    module_name, attr = _ATTR_MAP[name]
    module = import_module(module_name)
    value = getattr(module, attr)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
