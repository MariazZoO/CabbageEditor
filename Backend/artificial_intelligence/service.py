"""
服务入口薄层：转发到 Backend.artificial_intelligence.service.* 各子模块。
"""

from __future__ import annotations

import pathlib

# 将同名目录暴露为包，便于导入子模块
__path__ = [str(pathlib.Path(__file__).with_suffix(""))]
try:
    __spec__.submodule_search_locations = __path__  # type: ignore[attr-defined]
except Exception:
    pass

from Backend.artificial_intelligence.service import (  # noqa: E402
    chat,
    image,
    music,
    speech,
    text,
    video,
)

handle_integrated_entrance = chat.handle_integrated_entrance
handle_image_generation = image.handle_image_generation
handle_video_generation = video.handle_video_generation
handle_text_generation = text.handle_text_generation
handle_speech_generation = speech.handle_speech_generation
handle_music_generation = music.handle_music_generation

__all__ = [
    "handle_integrated_entrance",
    "handle_image_generation",
    "handle_video_generation",
    "handle_text_generation",
    "handle_speech_generation",
    "handle_music_generation",
]
