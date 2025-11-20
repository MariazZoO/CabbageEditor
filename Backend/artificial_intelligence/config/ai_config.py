"""
AI 专属配置
处理 LLM、图像生成、视频生成等 AI 相关配置
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from .ai_settings import AI_SETTINGS, DEFAULT_SYSTEM_PROMPT

_AI_CACHE: Optional["AIConfig"] = None


# ---------------------------------------------------------------------------
# dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderConfig:
    """AI 服务提供商配置"""

    name: str
    type: str = "openai"
    base_url: str | None = None
    api_key: str | None = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatModelConfig:
    """聊天模型配置"""

    provider: str
    model: str
    temperature: float
    request_timeout: float
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


@dataclass(frozen=True)
class ToolModelConfig:
    """工具模型配置"""

    provider: str
    model: str


@dataclass(frozen=True)
class MediaToolConfig:
    """媒体工具配置"""

    enable: bool = False
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class MediaConfig:
    """媒体配置（图像/视频）"""

    image: MediaToolConfig = field(default_factory=MediaToolConfig)
    video: MediaToolConfig = field(default_factory=MediaToolConfig)


@dataclass(frozen=True)
class TTSConfig:
    """TTS 配置"""

    appid: str | None = None
    token: str | None = None


@dataclass(frozen=True)
class MusicConfig:
    """音乐生成配置"""

    api_key: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class AIConfig:
    """AI 配置"""

    providers: Dict[str, ProviderConfig]
    chat: ChatModelConfig
    tool_models: Dict[str, ToolModelConfig]
    media: MediaConfig
    tts: TTSConfig
    music: MusicConfig


# ---------------------------------------------------------------------------
# 配置加载辅助函数
# ---------------------------------------------------------------------------


def _apply_env_overrides(data: Dict[str, Any]) -> None:
    """应用环境变量覆盖"""
    overrides = {
        ("llm", "chat", "model"): os.getenv("CORONA_LLM_MODEL"),
        ("llm", "chat", "provider"): os.getenv("CORONA_LLM_PROVIDER"),
    }
    for path, value in overrides.items():
        if value is None:
            continue
        section = data
        for part in path[:-1]:
            section = section.setdefault(part, {})
        key = path[-1]
        section[key] = value


def _load_ai_config_data() -> Dict[str, Any]:
    """从 ai_settings 模块加载配置"""
    data = copy.deepcopy(AI_SETTINGS)
    _apply_env_overrides(data)
    return data


# ---------------------------------------------------------------------------
# 解析辅助函数
# ---------------------------------------------------------------------------


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_providers(raw: Any) -> Dict[str, ProviderConfig]:
    providers: Dict[str, ProviderConfig] = {}
    entries = raw if isinstance(raw, list) else []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        name = entry.get("name")
        if not name:
            continue
        api_key = entry.get("api_key")
        api_key_env = entry.get("api_key_env")
        if api_key_env:
            api_key = os.getenv(str(api_key_env), api_key)
        headers = (
            entry.get("headers") if isinstance(entry.get("headers"), Mapping) else {}
        )
        providers[name] = ProviderConfig(
            name=name,
            type=str(entry.get("type", "openai")),
            base_url=entry.get("base_url"),
            api_key=api_key,
            headers={str(k): str(v) for k, v in headers.items()},
        )
    return providers


def _load_tool_models(raw: Mapping[str, Any]) -> Dict[str, ToolModelConfig]:
    tool_models: Dict[str, ToolModelConfig] = {}
    for name, cfg in raw.items():
        if not isinstance(cfg, Mapping):
            continue
        provider = cfg.get("provider")
        model = cfg.get("model")
        if not provider or not model:
            continue
        tool_models[name] = ToolModelConfig(provider=str(provider), model=str(model))
    return tool_models


def _load_media_config(raw: Mapping[str, Any]) -> MediaConfig:
    def _load_media_tool(section: Mapping[str, Any] | None) -> MediaToolConfig:
        if not isinstance(section, Mapping):
            return MediaToolConfig()
        return MediaToolConfig(
            enable=_as_bool(section.get("enable"), False),
            provider=section.get("provider"),
            model=section.get("model"),
            base_url=section.get("base_url"),
        )

    image = _load_media_tool(raw.get("image"))
    video = _load_media_tool(raw.get("video"))
    return MediaConfig(image=image, video=video)


def _load_tts_config(raw: Mapping[str, Any] | None) -> TTSConfig:
    """加载 TTS 配置"""
    if not isinstance(raw, Mapping):
        return TTSConfig()

    appid = raw.get("appid")
    appid_env = raw.get("appid_env")
    if appid_env:
        appid = os.getenv(str(appid_env), appid)

    token = raw.get("token")
    token_env = raw.get("token_env")
    if token_env:
        token = os.getenv(str(token_env), token)

    return TTSConfig(
        appid=appid,
        token=token,
    )


def _load_music_config(raw: Mapping[str, Any] | None) -> MusicConfig:
    """加载音乐生成配置"""
    if not isinstance(raw, Mapping):
        return MusicConfig()

    api_key = raw.get("api_key")
    api_key_env = raw.get("api_key_env")
    if api_key_env:
        api_key = os.getenv(str(api_key_env), api_key)

    base_url = raw.get("base_url")

    return MusicConfig(
        api_key=api_key,
        base_url=base_url,
    )


# ---------------------------------------------------------------------------
# 公共函数
# ---------------------------------------------------------------------------


def _build_ai_config() -> AIConfig:
    """构建 AI 配置"""
    raw = _load_ai_config_data()

    providers = _load_providers(raw.get("providers"))
    if not providers:
        raise RuntimeError("AI 配置中至少需要声明一个 provider")

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
    tts = _load_tts_config(raw.get("tts"))
    music = _load_music_config(raw.get("music"))

    return AIConfig(
        providers=providers,
        chat=chat,
        tool_models=tool_models,
        media=media,
        tts=tts,
        music=music,
    )


def get_ai_config() -> AIConfig:
    """获取 AI 配置（单例）"""
    global _AI_CACHE
    if _AI_CACHE is None:
        _AI_CACHE = _build_ai_config()
    return _AI_CACHE


def reload_ai_config() -> AIConfig:
    """重新加载 AI 配置"""
    global _AI_CACHE
    _AI_CACHE = _build_ai_config()
    return _AI_CACHE


__all__ = [
    "AIConfig",
    "ProviderConfig",
    "ChatModelConfig",
    "ToolModelConfig",
    "MediaConfig",
    "MediaToolConfig",
    "TTSConfig",
    "MusicConfig",
    "get_ai_config",
    "reload_ai_config",
]
