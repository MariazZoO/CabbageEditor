"""
配置兼容性包装器
旧代码从这里导入配置，实际指向新的配置结构

新的配置结构:
- 全局配置: config/app_config.py  (运行时、路径)
- AI 配置: Backend/artificial_intelligence/config/ai_config.py  (LLM、媒体工具)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import sys

# 添加项目根目录到路径
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# 导入新的配置模块
from config.app_config import get_app_config as get_global_config
from config.runtime_config import RuntimeConfig
from config.paths_config import PathsConfig
from .ai_config import (
    get_ai_config,
    reload_ai_config,
    ProviderConfig,
    ChatModelConfig,
    ToolModelConfig,
    MediaConfig,
    MediaToolConfig,
)

_CACHE: Optional["AppConfig"] = None
DEFAULT_SYSTEM_PROMPT = (
    "你是 CabbageEditor 的内置助手。请在回答前检查可用工具，必要时调用 MCP、图像或视频工具；其余情况直接用中文简洁回答。"
)



# ---------------------------------------------------------------------------
# 兼容性 AppConfig（合并全局配置和 AI 配置）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AppConfig:
    """
    兼容性配置类
    合并了全局配置和 AI 配置，保持与旧代码的兼容
    """
    providers: Dict[str, ProviderConfig]
    chat: ChatModelConfig
    tool_models: Dict[str, ToolModelConfig]
    media: MediaConfig
    runtime: RuntimeConfig
    paths: PathsConfig


# ---------------------------------------------------------------------------
# 兼容性包装函数
# ---------------------------------------------------------------------------


def _build_app_config() -> AppConfig:
    """
    构建兼容的 AppConfig 对象
    合并全局配置和 AI 配置
    """
    # 加载全局配置
    global_config = get_global_config()

    # 加载 AI 配置
    ai_config = get_ai_config()

    # 合并为兼容的 AppConfig
    return AppConfig(
        providers=ai_config.providers,
        chat=ai_config.chat,
        tool_models=ai_config.tool_models,
        media=ai_config.media,
        runtime=global_config.runtime,
        paths=global_config.paths,
    )


def get_app_config() -> AppConfig:
    global _CACHE
    if _CACHE is None:
        _CACHE = _build_app_config()
    return _CACHE


def reload_app_config() -> AppConfig:
    global _CACHE
    _CACHE = _build_app_config()
    return _CACHE


__all__ = [
    "AppConfig",
    "ProviderConfig",
    "ChatModelConfig",
    "ToolModelConfig",
    "MediaConfig",
    "MediaToolConfig",
    "RuntimeConfig",
    "PathsConfig",
    "get_app_config",
    "reload_app_config",
]
