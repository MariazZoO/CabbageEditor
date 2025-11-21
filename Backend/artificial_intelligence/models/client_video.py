"""
DashScope 视频生成客户端
提供图生视频功能
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Dict, Any
from dashscope import VideoSynthesis
import dashscope

from Backend.artificial_intelligence.config.ai_config import ProviderConfig
from Backend.artificial_intelligence.models.video_utils import TaskPoller, retry_operation


class DashScopeVideoClient:
    """
    DashScope 视频生成客户端

    支持图生视频功能，基于异步任务和轮询机制
    """

    def __init__(
        self,
        provider: ProviderConfig,
        model: str = "wan2.2-i2v-flash",
        base_url: str | None = None,
    ):
        """
        初始化视频生成客户端

        参数:
        - provider: 提供商配置（包含 API Key）
        - model: 模型名称
        - base_url: API 基础 URL（可选）
        """
        if not provider.api_key:
            raise RuntimeError(f"Provider '{provider.name}' 缺少 API Key")

        self.provider = provider
        self.model = model
        self.api_key = provider.api_key

        # 设置 DashScope API 基础 URL
        if base_url:
            dashscope.base_http_api_url = base_url
        elif provider.base_url:
            dashscope.base_http_api_url = provider.base_url
        else:
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    @retry_operation(max_retries=3)
    def generate_video_from_image(
        self,
        *,
        prompt: str,
        image_url: str,
        resolution: str = "720P",
        prompt_extend: bool = True,
        max_wait_seconds: int = 600,
        poll_interval: float = 5.0,
    ) -> Dict[str, Any]:
        """
        从图片生成视频

        参数:
        - prompt: 视频生成提示词
        - image_url: 图片 URL，支持：
            * file:// 本地文件路径（如 file:///path/to/image.jpg）
            * http:// 或 https:// 网络图片
            * data:image/...;base64,... data URI
        - resolution: 视频分辨率（480P/720P/1080P）
        - prompt_extend: 是否扩展提示词
        - max_wait_seconds: 最大等待时间（秒）
        - poll_interval: 轮询间隔（秒）

        返回:
        - 包含视频 URL 和元数据的字典
        """
        # 提交异步任务
        rsp = VideoSynthesis.async_call(
            api_key=self.api_key,
            model=self.model,
            prompt=prompt,
            img_url=image_url,
            resolution=resolution,
            prompt_extend=prompt_extend,
            watermark=False,
            negative_prompt="",
        )

        if rsp.status_code != HTTPStatus.OK:
            raise RuntimeError(
                f"视频生成任务提交失败: status_code={rsp.status_code}, "
                f"code={rsp.code}, message={rsp.message}"
            )

        task_id = rsp.output.task_id

        # 轮询任务状态
        poller = TaskPoller(
            api_key=self.api_key, interval=poll_interval, timeout=max_wait_seconds
        )
        result = poller.poll(task_id)

        return result


__all__ = ["DashScopeVideoClient"]
