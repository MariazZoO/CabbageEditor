"""GUI utilities - Requires PySide6."""

# 延迟导入，避免在服务器模式下导入失败
_GUI_AVAILABLE = False

try:
    from .central_manager import CentralManager
    from .dialogs import FileHandler
    from .static_components import url
    from .script_runner import ScriptRunner
    _GUI_AVAILABLE = True
except Exception as e:
    # 服务器模式下或配置问题时，GUI 模块不可用
    import warnings
    warnings.warn(f"GUI utilities not available: {e}", ImportWarning)

    CentralManager = None
    FileHandler = None
    url = None
    ScriptRunner = None

__all__ = [
    "CentralManager",
    "FileHandler",
    "url",
    "ScriptRunner",
    "_GUI_AVAILABLE",
]

