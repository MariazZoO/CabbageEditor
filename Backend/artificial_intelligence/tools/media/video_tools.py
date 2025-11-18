"""
视频生成工具
提供基于 LangChain 的视频生成功能（图生视频）
"""

from __future__ import annotations

import json
from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.config import AppConfig, MediaToolConfig
from Backend.artificial_intelligence.models.client_video import DashScopeVideoClient
from Backend.artificial_intelligence.models.video_utils import resolve_image_url
from Backend.artificial_intelligence.storage import get_media_store
from Backend.artificial_intelligence.tools.session import get_current_session


class VideoGenerationInput(BaseModel):
    """视频生成输入参数

    此类定义了图生视频功能所需的所有参数。
    支持基于单张图片和文本提示词生成动态视频内容。
    """

    prompt: str = Field(
        ...,
        description=(
            "视频生成提示词，用于描述要生成的视频内容。"
            "应详细描述视频中的动作、场景、运动方式、氛围等元素。"
            "例如：'镜头缓慢推进，树叶在微风中轻轻摇曳，阳光透过枝叶洒下斑驳光影'。"
            "提示词越详细，生成的视频效果越精确。"
        ),
    )
    image_url: str = Field(
        ...,
        description=(
            "输入图片的 URL，作为视频生成的起始帧。支持以下三种格式："
            "\n1) autosave:// URL - 当前会话中上传或 AI 生成的图片，例如 'autosave://session_id/generated/image.png'；"
            "\n2) data:image/...;base64,... - Base64 编码的图片数据 URI；"
            "\n3) 本地文件路径 - 系统中的绝对或相对文件路径。"
            "\n注意：图片会被解析并转换为模型可接受的格式，如果图片无法加载将返回错误。"
        ),
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "会话 ID，用于标识和隔离不同用户或对话的媒体资源。"
            "如果省略此参数，系统会自动使用当前活跃的聊天会话 ID。"
            "生成的视频将保存在对应会话的 generated 目录下。"
        ),
    )
    resolution: str = Field(
        default="720P",
        description=(
            "视频输出分辨率，影响视频清晰度和文件大小。"
            "支持三种规格："
            "\n- '480P'：标清，文件较小，生成速度较快；"
            "\n- '720P'：高清，平衡质量与性能（默认推荐）；"
            "\n- '1080P'：全高清，最佳画质但文件较大，生成时间较长。"
            "\n注意：必须使用准确的字符串值（区分大小写），否则会返回参数错误。"
        ),
    )
    prompt_extend: bool = Field(
        default=True,
        description=(
            "是否启用提示词智能扩展功能。"
            "当设置为 True 时，模型会自动优化和扩展用户的提示词，补充更多细节以提升生成质量。"
            "扩展后的提示词会在返回结果的 'actual_prompt' 字段中体现，"
            "原始提示词会保留在 'orig_prompt' 字段中。"
            "建议保持默认开启以获得更好的视频效果。"
        ),
    )
    download_video: bool = Field(
        default=True,
        description=(
            "是否自动下载生成的视频到本地存储。"
            "当设置为 True 时，视频会从云端下载到 autosave/<session_id>/generated/ 目录，"
            "并在返回结果的 'local_video' 字段中提供本地路径、文件大小等信息。"
            "如果下载失败，不会影响主流程，但会在 'download_error' 字段中记录错误信息。"
            "设置为 False 仅返回云端视频 URL，不进行本地存储。"
        ),
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
    media_store = get_media_store()

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

        # 使用不同的变量名避免覆盖参数
        active_session_id = data.session_id or get_current_session()

        # 验证分辨率参数
        valid_resolutions = {"480P", "720P", "1080P"}
        if data.resolution not in valid_resolutions:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": f"无效的分辨率: {data.resolution}，支持的值: {', '.join(valid_resolutions)}",
                    "session_id": active_session_id,
                },
                ensure_ascii=False,
            )

        # 准备图片 URL
        image_url = resolve_image_url(data.image_url, media_store)
        if not image_url:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": f"无法加载图片：{data.image_url}",
                    "session_id": active_session_id,
                },
                ensure_ascii=False,
            )

        # 生成视频
        try:
            result = client.generate_video_from_image(
                prompt=data.prompt,
                image_url=image_url,
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
                "session_id": active_session_id,
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
                    stored_video = media_store.download_and_save_video(
                        session_id=active_session_id,
                        video_url=payload["video_url"],
                        task_id=payload["task_id"],
                        prompt=data.prompt,
                        source_image_url=data.image_url,
                    )

                    # 添加本地存储信息
                    payload["local_video"] = {
                        "name": stored_video.name,
                        "path": str(stored_video.path),
                        "url": media_store.build_video_url(stored_video),
                        "file_size_mb": stored_video.file_size_mb,
                    }
                except Exception as e:
                    # 下载失败不影响主流程，但记录错误信息
                    import logging

                    logging.getLogger(__name__).warning(
                        f"视频下载失败 (session={active_session_id}, task={payload['task_id']}): {e}"
                    )
                    payload["download_error"] = str(e)

            return json.dumps(payload, ensure_ascii=False)

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"视频生成失败 (session={active_session_id}): {e}", exc_info=True
            )
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": str(e),
                    "session_id": active_session_id,
                },
                ensure_ascii=False,
            )

    tool = StructuredTool(
        name="generate_video_from_image",
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


__all__ = ["load_video_tools"]
