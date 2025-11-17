"""
DashScope 视频生成客户端
封装图生视频 (Image-to-Video) 功能
"""

from __future__ import annotations

import base64
import os
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict, Tuple
from PIL import Image


import dashscope
from dashscope import VideoSynthesis

from Backend.artificial_intelligence.config.config import ProviderConfig
from Backend.artificial_intelligence.models.task_poller import TaskPoller


class DashScopeVideoClient:
    """
    DashScope 视频生成客户端

    支持：
    - 图生视频 (Image-to-Video)
    - 异步任务提交和轮询
    - 自动图片分辨率调整
    """

    def __init__(
        self,
        *,
        provider: ProviderConfig,
        model: str = "wan2.2-i2v-flash",
        base_url: str | None = None,
    ):
        """
        初始化视频生成客户端

        参数:
        - provider: 提供商配置（需包含 api_key）
        - model: 模型名称，默认 "wan2.2-i2v-flash"
        - base_url: API 基础 URL（可选）
        """
        if not provider.api_key:
            raise RuntimeError(f"Provider '{provider.name}' 缺少 API Key。")

        self.provider = provider
        self.model = model
        self.api_key = provider.api_key

        # 设置 DashScope 配置
        if base_url:
            dashscope.base_http_api_url = base_url
        elif provider.base_url:
            dashscope.base_http_api_url = provider.base_url

    def generate_video_from_image(
        self,
        *,
        prompt: str,
        image_b64: str,
        resolution: str = "720P",
        prompt_extend: bool = True,
        watermark: bool = False,
        negative_prompt: str = "",
        seed: int | None = None,
        max_wait_seconds: float = 600,
        poll_interval: float = 5.0,
    ) -> Dict[str, Any]:
        """
        图生视频：根据图片和提示词生成视频

        参数:
        - prompt: 视频生成提示词
        - image_b64: Base64 编码的图片
        - resolution: 分辨率（480P/720P/1080P）
        - prompt_extend: 是否扩展提示词
        - watermark: 是否添加水印
        - negative_prompt: 负面提示词
        - seed: 随机种子（可选）
        - max_wait_seconds: 最大等待时间（秒）
        - poll_interval: 轮询间隔（秒）

        返回:
        - 包含视频 URL 和元数据的字典
        """
        # 1. 提交异步任务
        task_id = self._submit_task(
            prompt=prompt,
            image_b64=image_b64,
            resolution=resolution,
            prompt_extend=prompt_extend,
            watermark=watermark,
            negative_prompt=negative_prompt,
            seed=seed,
        )

        # 2. 轮询任务状态
        poller = TaskPoller(
            api_key=self.api_key,
            interval=poll_interval,
            timeout=max_wait_seconds,
        )
        result = poller.poll(task_id)

        return result

    def _submit_task(
        self,
        *,
        prompt: str,
        image_b64: str,
        resolution: str,
        prompt_extend: bool,
        watermark: bool,
        negative_prompt: str,
        seed: int | None,
    ) -> str:
        """
        提交视频生成任务

        返回:
        - task_id: 任务 ID
        """
        # 构建图片 URL (使用 base64 data URI)
        img_url = f"data:image/png;base64,{image_b64}"

        # 构建请求参数
        params = {
            "api_key": self.api_key,
            "model": self.model,
            "prompt": prompt,
            "img_url": img_url,
            "resolution": resolution,
            "prompt_extend": prompt_extend,
            "watermark": watermark,
            "negative_prompt": negative_prompt,
        }

        # 添加可选参数
        if seed is not None:
            params["seed"] = seed

        # 提交异步任务
        print("\n📤 提交视频生成任务...")
        print(f"   模型: {self.model}")
        print(f"   分辨率: {resolution}")
        print(f"   提示词扩展: {prompt_extend}")

        response = VideoSynthesis.async_call(**params)

        if response.status_code == HTTPStatus.OK:
            task_id = response.output.task_id
            task_status = response.output.task_status
            print("✓ 任务已提交")
            print(f"  任务ID: {task_id}")
            print(f"  初始状态: {task_status}")
            return task_id
        else:
            raise RuntimeError(
                f"任务提交失败: status_code={response.status_code}, "
                f"code={response.code}, message={response.message}"
            )


class ImageProcessor:
    """图片预处理工具"""

    @staticmethod
    def resize_image_with_constraints(
        image_path: str,
        target_width: int | None = None,
        target_height: int | None = None,
        max_size: int = 2000,
        min_size: int = 360,
    ) -> str:
        """
        调整图片分辨率，确保宽高在指定范围内

        参数:
        - image_path: 图片路径
        - target_width: 目标宽度（可选）
        - target_height: 目标高度（可选）
        - max_size: 最大尺寸，默认 2000
        - min_size: 最小尺寸，默认 360

        返回:
        - 调整后的图片路径
        """
        img = Image.open(image_path)
        original_width, original_height = img.size

        # 验证目标尺寸范围
        if target_width is not None:
            if target_width < min_size or target_width > max_size:
                raise ValueError(
                    f"目标宽度必须在 [{min_size}, {max_size}] 范围内，"
                    f"当前值: {target_width}"
                )

        if target_height is not None:
            if target_height < min_size or target_height > max_size:
                raise ValueError(
                    f"目标高度必须在 [{min_size}, {max_size}] 范围内，"
                    f"当前值: {target_height}"
                )

        # 计算新尺寸
        new_width, new_height = ImageProcessor._calculate_new_size(
            original_width,
            original_height,
            target_width,
            target_height,
            max_size,
            min_size,
        )

        # 调整图片大小
        if (new_width, new_height) != (original_width, original_height):
            resized_img = img.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS,
            )

            # 保存调整后的图片
            output_path = Path(image_path).parent / f"resized_{Path(image_path).name}"
            resized_img.save(output_path, quality=95)

            return str(output_path)
        else:
            return image_path

    @staticmethod
    def _calculate_new_size(
        original_width: int,
        original_height: int,
        target_width: int | None,
        target_height: int | None,
        max_size: int,
        min_size: int,
    ) -> Tuple[int, int]:
        """计算新的图片尺寸"""
        if target_width and target_height:
            # 指定了宽和高
            new_width = target_width
            new_height = target_height
        elif target_width:
            # 只指定了宽度，按比例计算高度
            ratio = target_width / original_width
            new_width = target_width
            new_height = int(original_height * ratio)
        elif target_height:
            # 只指定了高度，按比例计算宽度
            ratio = target_height / original_height
            new_width = int(original_width * ratio)
            new_height = target_height
        else:
            # 未指定，自动调整以满足范围要求
            new_width = original_width
            new_height = original_height

            # 如果超过最大值，等比例缩小
            if new_width > max_size or new_height > max_size:
                ratio = min(max_size / new_width, max_size / new_height)
                new_width = int(new_width * ratio)
                new_height = int(new_height * ratio)

            # 如果小于最小值，等比例放大
            if new_width < min_size or new_height < min_size:
                ratio = max(min_size / new_width, min_size / new_height)
                new_width = int(new_width * ratio)
                new_height = int(new_height * ratio)

        # 再次确保在范围内
        new_width = max(min_size, min(max_size, new_width))
        new_height = max(min_size, min(max_size, new_height))

        return new_width, new_height

    @staticmethod
    def load_image_as_base64(image_path: str) -> str:
        """
        加载图片并转换为 Base64 编码

        参数:
        - image_path: 图片路径

        返回:
        - Base64 编码字符串
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


__all__ = ["DashScopeVideoClient", "ImageProcessor"]
