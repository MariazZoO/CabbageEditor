from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import os
import tomllib

APP_CONFIG_FILE = Path(__file__).with_name("app_config.toml")
APP_CONFIG_TEMPLATE = Path(__file__).with_name("app_config.example.toml")
USER_CONFIG_FILE = Path.home() / ".coronaengine" / "app_config.toml"
DEFAULT_SYSTEM_PROMPT = (
    "你是 CabbageEditor 的内置助手。请在回答前检查可用工具，必要时调用 MCP、图像或视频工具；其余情况直接用中文简洁回答。"
)

@dataclass(frozen=True)
class AppConfig:
    providers: Dict[str, ProviderConfig]
    chat: ChatModelConfig
    tool_models: Dict[str, ToolModelConfig]
    media: MediaConfig
    runtime: RuntimeConfig
    paths: PathsConfig

# ---------------------------------------------------------------------------
# public load function
# ---------------------------------------------------------------------------
_CACHE: Optional["AppConfig"] = None


def _build_app_config() -> AppConfig:
    raw = _load_config_data()

    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root / "Backend"
    autosave_dir = repo_root / "autosave"
    autosave_dir.mkdir(parents=True, exist_ok=True)
    paths = PathsConfig(
        repo_root=repo_root,
        backend_root=backend_root,
        frontend_dist=repo_root / "Frontend" / "dist" / "index.html",
        script_dir=backend_root / "script",
        autosave_dir=autosave_dir,
    )

    providers = _load_providers(raw.get("providers"))
    if not providers:
        raise RuntimeError("app_config.toml 中至少需要声明一个 [[providers]]")

    llm_section = raw.get("llm", {})
    chat_section = llm_section.get("chat", llm_section)
    chat = ChatModelConfig(
        provider=str(chat_section.get("provider", next(iter(providers.keys())))),
        model=str(chat_section.get("model", "Qwen/Qwen2.5-7B-Instruct")),
        temperature=_as_float(chat_section.get("temperature", 0.2), 0.2),
        request_timeout=_as_float(chat_section.get("request_timeout", 60), 60.0),
        system_prompt=str(chat_section.get("system_prompt", DEFAULT_SYSTEM_PROMPT)),
    )

    tool_models = _load_tool_models(llm_section.get("tool_models", {}))

    media = _load_media_config(raw.get("media", {}))

    runtime_data = raw.get("runtime", {})
    runtime = RuntimeConfig(
        enable_gpu=_as_bool(runtime_data.get("enable_gpu"), False),
        log_level=str(runtime_data.get("log_level", "INFO")).upper(),
    )

    return AppConfig(
        providers=providers,
        chat=chat,
        tool_models=tool_models,
        media=media,
        runtime=runtime,
        paths=paths,
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
    "get_app_config",
    "reload_app_config",
]