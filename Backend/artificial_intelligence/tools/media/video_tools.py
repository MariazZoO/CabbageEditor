"""
视频生成工具
提供基于 LangChain 的视频生成功能（图生视频）
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.config import AppConfig, MediaToolConfig
from Backend.artificial_intelligence.models.video_client import DashScopeVideoClient
from Backend.artificial_intelligence.tools.storage import (
    get_image_store,
    AUTOSAVE_URL_SCHEME,
)
from Backend.artificial_intelligence.tools.video_storage import get_video_store
from Backend.artificial_intelligence.tools.session import get_current_session


class VideoGenerationInput(BaseModel):
    """视频生成输入参数"""

    prompt: str = Field(
        ...,
        description="视频生成提示词，描述要生成的视频内容、动作、场景等",
    )
    image_url: str = Field(
        ...,
        description=(
            "输入图片的 URL，支持以下格式："
            "1) autosave:// URL（会话中上传或生成的图片）；"
            "2) data:image/...;base64,... URI；"
            "3) 本地文件路径"
        ),
    )
    session_id: str | None = Field(
        default=None,
        description="会话 ID；若省略则自动使用当前聊天会话",
    )
    resolution: str = Field(
        default="720P",
        description="视频分辨率，支持 480P、720P、1080P",
    )
    prompt_extend: bool = Field(
        default=True,
        description="是否进行提示词扩展以获得更好的生成效果",
    )
    download_video: bool = Field(
        default=True,
        description="是否自动下载视频到本地（默认为 True）",
    )


def load_video_tools(config: AppConfig) -> List[StructuredTool]:
    """
    加载视频生成工具

    参数:
    - config: 应用配置

    返回:
    - LangChain StructuredTool 列表
    """
    video_cfg = config.media.video
    if not _is_media_tool_enabled(video_cfg, config):
        return []

    provider = config.providers[video_cfg.provider]
    client = DashScopeVideoClient(
        provider=provider,
        model=video_cfg.model or "wan2.2-i2v-flash",
        base_url=video_cfg.base_url,
    )
    image_store = get_image_store()
    video_store = get_video_store()

    def _generate_video(
        prompt: str,
        image_url: str,
        session_id: str | None = None,
        resolution: str = "720P",
        prompt_extend: bool = True,
        download_video: bool = True,
    ) -> str:
        """图生视频：根据图片和提示词生成视频。"""
        data = VideoGenerationInput(
            prompt=prompt,
            image_url=image_url,
            session_id=session_id,
            resolution=resolution,
            prompt_extend=prompt_extend,
            download_video=download_video,
        )

        session_id = data.session_id or get_current_session()

        # 加载图片
        image_b64 = _load_image_base64(image_store, data.image_url)
        if not image_b64:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": f"无法加载图片：{data.image_url}",
                    "session_id": session_id,
                },
                ensure_ascii=False,
            )

        # 生成视频
        try:
            result = client.generate_video_from_image(
                prompt=data.prompt,
                image_b64=image_b64,
                resolution=data.resolution,
                prompt_extend=data.prompt_extend,
                max_wait_seconds=600,
                poll_interval=5.0,
            )

            # 构建响应数据
            payload = {
                "type": "video_generation",
                "status": "succeeded",
                "prompt": data.prompt,
                "source": provider.name,
                "model": client.model,
                "video_url": result.get("output", {}).get("video_url"),
                "task_id": result.get("task_id"),
                "resolution": data.resolution,
                "session_id": session_id,
            }

            # 添加可选字段
            output = result.get("output", {})
            if "orig_prompt" in output:
                payload["orig_prompt"] = output["orig_prompt"]
            if "actual_prompt" in output:
                payload["actual_prompt"] = output["actual_prompt"]
            if "usage" in result:
                payload["usage"] = result["usage"]

            # 如果需要，下载视频到本地
            if download_video and payload["video_url"]:
                try:
                    stored_video = video_store.download_and_save(
                        session_id=session_id,
                        video_url=payload["video_url"],
                        task_id=payload["task_id"],
                        prompt=data.prompt,
                        source_image_url=data.image_url,
                    )

                    # 添加本地存储信息
                    payload["local_video"] = {
                        "name": stored_video.name,
                        "path": str(stored_video.path),
                        "url": video_store.build_url(stored_video),
                        "file_size_mb": stored_video.file_size_mb,
                    }
                except Exception as e:
                    # 下载失败不影响主流程
                    payload["download_error"] = str(e)

            return json.dumps(payload, ensure_ascii=False)

        except Exception as e:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": str(e),
                    "session_id": session_id,
                },
                ensure_ascii=False,
            )

    tool = StructuredTool(
        name="generate_video",
        description=(
            "根据图片和文本提示词生成视频（图生视频）。"
            "输入需要包含："
            "1) 视频生成提示词（描述动作、场景、运动等）；"
            "2) 输入图片的 URL（支持 autosave:// URL、base64 data URI 或本地文件路径）。"
            "可选参数包括分辨率（480P/720P/1080P，默认720P）和提示词扩展开关（默认开启）。"
            "生成的视频会自动下载到本地并返回本地路径。"
        ),
        args_schema=VideoGenerationInput,
        func=_generate_video,
    )
    return [tool]


def _is_media_tool_enabled(cfg: MediaToolConfig, config: AppConfig) -> bool:
    """检查媒体工具是否启用"""
    if not cfg.enable:
        return False
    if not cfg.provider or not cfg.model:
        return False
    if cfg.provider not in config.providers:
        return False
    provider = config.providers[cfg.provider]
    return bool(provider.api_key)


def _load_image_base64(store, source: Optional[str]) -> Optional[str]:
    """从 autosave:// URL、base64 URI 或本地路径加载图片并转换为 base64。"""
    if not source:
        return None

    # 处理 data URI (base64)
    if source.startswith("data:"):
        # 格式：data:image/png;base64,iVBORw0KGgo...
        if ";base64," in source:
            # 提取 base64 部分
            return source.split(";base64,", 1)[1]
        else:
            # 不支持非 base64 的 data URI
            return None

    # 处理 autosave:// URL
    if source.startswith(AUTOSAVE_URL_SCHEME):
        stored = store.resolve_url(source)
        if stored and stored.path.exists():
            return base64.b64encode(stored.path.read_bytes()).decode("utf-8")
        return None

    # 尝试作为本地路径
    candidate = Path(source)
    if candidate.exists():
        return base64.b64encode(candidate.read_bytes()).decode("utf-8")

    return None


__all__ = ["load_video_tools"]
