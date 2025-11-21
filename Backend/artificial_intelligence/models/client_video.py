"""
DashScope 视频生成客户端
提供图生视频功能
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Dict, Any, Tuple, Optional
from dashscope import VideoSynthesis
import dashscope

from Backend.artificial_intelligence.config.ai_config import ProviderConfig
from Backend.artificial_intelligence.models.utils import retry_operation, TaskPoller, BaseAPIClient


class DashScopeVideoClient(BaseAPIClient):
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
        super().__init__(provider, base_url)
        self.model = model

        # 设置 DashScope API 基础 URL
        if self.base_url:
            dashscope.base_http_api_url = self.base_url
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
        poller = TaskPoller(interval=poll_interval, timeout=max_wait_seconds)

        def check_status(tid: str) -> Tuple[str, Any, Optional[str]]:
            response = VideoSynthesis.fetch(
                api_key=self.api_key,
                task=tid,
            )

            if response.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"查询任务状态失败: status_code={response.status_code}, "
                    f"code={response.code}, message={response.message}"
                )

            status = response.output.task_status
            result = None
            error = None

            if status == "SUCCEEDED":
                result = self._build_result(response)
            elif status == "FAILED":
                error = getattr(response.output, "message", "未知错误")

            return status, result, error

        return poller.poll(task_id, check_status)

    def _build_result(self, response) -> Dict[str, Any]:
        """构建任务结果字典"""
        output = response.output
        usage = response.usage if hasattr(response, "usage") else {}

        result = {
            "task_id": output.task_id,
            "task_status": output.task_status,
            "output": {
                "video_url": getattr(output, "video_url", None),
            },
            "usage": {},
        }

        # 添加可选的输出字段
        optional_fields = [
            "orig_prompt",
            "actual_prompt",
            "submit_time",
            "scheduled_time",
            "end_time",
        ]
        for field in optional_fields:
            if hasattr(output, field):
                result["output"][field] = getattr(output, field)

        if usage:
            result["usage"] = {
                "video_count": getattr(usage, "video_count", 0),
            }

        return result


__all__ = ["DashScopeVideoClient"]
