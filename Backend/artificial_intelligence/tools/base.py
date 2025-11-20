from __future__ import annotations

from langchain_core.tools import BaseTool

from Backend.artificial_intelligence.config.ai_config import AIConfig
from Backend.artificial_intelligence.tools.builtin import load_builtin_tools
from Backend.artificial_intelligence.tools.text import load_text_tools
from Backend.artificial_intelligence.tools.mcp import load_mcp_tools
from Backend.artificial_intelligence.tools.media.image_tools import load_image_tools
from Backend.artificial_intelligence.tools.media.video_tools import load_video_tools
from Backend.artificial_intelligence.tools.media.speech_tools import load_speech_tools
from Backend.artificial_intelligence.tools.media.music_tools import load_music_tools


def load_tools(config: AIConfig) -> list[BaseTool]:
    tools: list[BaseTool] = []
    tools.extend(load_builtin_tools())
    tools.extend(load_text_tools(config))
    tools.extend(load_mcp_tools(config))
    tools.extend(load_image_tools(config))
    tools.extend(load_video_tools(config))
    tools.extend(load_speech_tools(config))
    tools.extend(load_music_tools(config))
    return tools


__all__ = ["load_tools"]
