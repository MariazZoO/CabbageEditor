"""
文本到背景音乐 (BGM) 生成工具

基于 Suno API 的简单封装：根据文本提示词生成可用作背景音乐的音频。
"""

from __future__ import annotations

import os
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.ai_config import AIConfig, ProviderConfig
from Backend.artificial_intelligence.models.client_music import SunoMusicClient
from Backend.artificial_intelligence.tools.response_adapter import (
    build_part,
    build_success_result,
    build_error_result,
)

_DEFAULT_BASE_URL = "https://api.sunoapi.org"


class TextToBGMInput(BaseModel):
    """文本到背景音乐生成输入"""

    prompt: str = Field(..., description="音乐内容或氛围的描述性文本提示词")
    style: Optional[str] = Field(
        default=None,
        description="可选的风格标签，例如 'lofi', 'ambient', 'fantasy', 'epic orchestral' 等",
    )
    model: str = Field(
        default="V5",
        description="Suno 模型版本，例如: V5, V4_5PLUS, V4_5, V4, V3_5",
    )
    duration: int = Field(
        default=20,
        description="期望的音乐时长（秒）。不同模型可能有上限，超出会被后端裁剪或拒绝。",
    )
    wait: bool = Field(
        default=True,
        description="是否同步等待任务完成。True 将轮询任务详情并在成功后下载音频。False 立即返回任务ID。",
    )
    max_wait_seconds: int = Field(
        default=600,
        description="最大等待时间（秒），仅在 wait=True 时生效。",
    )
    poll_interval: float = Field(
        default=3.0,
        description="轮询间隔（秒），仅在 wait=True 时生效。",
    )


def _resolve_suno_provider(config: AIConfig) -> Optional[ProviderConfig]:
    """
    解析 Suno API 配置，优先级：
    1. config.music 配置（独立配置项）
    2. 环境变量 SUNO_API_KEY
    """
    music_cfg = config.music
    api_key = music_cfg.api_key if music_cfg else None
    base_url = music_cfg.base_url if music_cfg else _DEFAULT_BASE_URL

    # 如果没有配置，尝试从环境变量读取
    if not api_key:
        api_key = os.getenv("SUNO_API_KEY")

    if not api_key:
        return None

    return ProviderConfig(
        name="suno",
        type="http",
        base_url=(base_url or _DEFAULT_BASE_URL).rstrip("/"),
        api_key=api_key.strip(),
    )


def load_music_tools(config: AIConfig):
    provider = _resolve_suno_provider(config)
    if provider is None:
        # 未配置 API Key 时不加载工具，保持系统正常
        print(
            "[警告] 未找到 Suno API 密钥，文本到BGM工具未启用。请设置环境变量 SUNO_API_KEY 或在 app_config.toml 中配置 provider 'suno'."
        )
        return []

    client = SunoMusicClient(provider)

    def _generate_bgm(
        prompt: str,
        style: str | None = None,
        model: str = "V5",
        duration: int = 20,
        wait: bool = True,
        max_wait_seconds: int = 600,
        poll_interval: float = 3.0,
    ) -> str:
        data = TextToBGMInput(
            prompt=prompt,
            style=style,
            model=model,
            duration=duration,
            wait=wait,
            max_wait_seconds=max_wait_seconds,
            poll_interval=poll_interval,
        )

        if not data.prompt.strip():
            return build_error_result(error_message="提示词不能为空").to_envelope(
                interface_type="music"
            )

        try:
            result = client.generate_music(
                prompt=data.prompt,
                style=data.style,
                model=data.model,
                wait=data.wait,
                max_wait_seconds=data.max_wait_seconds,
                poll_interval=data.poll_interval,
            )
        except Exception as e:
            return build_error_result(error_message=str(e)).to_envelope(interface_type="music")

        # 异步返回
        if not data.wait:
            part = build_part(
                content_type="text",
                content_text=f"任务已提交，ID: {result.get('task_id')}",
                parameter={
                    "music_style": data.style,
                },
            )
            return build_success_result(
                parts=[part],
            ).to_envelope(interface_type="music")

        # 同步返回结果
        if isinstance(result, list) and len(result) > 0:
            parts = []
            for item in result:
                audio_url = item.get("audio_url")
                if not audio_url:
                    continue

                part = build_part(
                    content_type="audio",
                    content_text=item.get("title") or data.prompt,
                    content_url=audio_url,
                    parameter={
                        "duration": item.get("duration"),
                        "music_style": data.style,
                        "image_url": item.get("image_url"),
                    },
                )
                parts.append(part)

            return build_success_result(
                parts=parts,
            ).to_envelope(interface_type="music")

        return build_error_result(error_message="未在结果中找到音频数据").to_envelope(
            interface_type="music"
        )

    tool = StructuredTool(
        name="generate_bgm_music",
        description=(
            "根据文本提示词生成背景音乐 (BGM)。支持指定模型版本、风格标签；"
            "可选择同步等待生成完成或立即返回任务ID。"
            "返回 JSON 字符串，包含任务ID、状态、可用的音频URL列表。"
        ),
        args_schema=TextToBGMInput,
        func=_generate_bgm,
    )

    return [tool]


__all__ = ["load_music_tools"]
