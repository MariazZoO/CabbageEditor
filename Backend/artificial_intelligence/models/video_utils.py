"""
视频生成工具集
整合图片处理、任务轮询、视频下载等实用功能
"""

from __future__ import annotations

import time
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, Dict

from dashscope import VideoSynthesis
from PIL import Image


# ========== 图片处理工具 ==========


def resize_image_with_constraints(
    image_path: str | Path,
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
    - max_size: 最大尺寸，默认2000
    - min_size: 最小尺寸，默认360

    返回:
    - 调整后的图片路径（如果无需调整则返回原路径）
    """
    image_path = Path(image_path)
    img = Image.open(image_path)
    original_width, original_height = img.size

    # 验证目标尺寸范围
    if target_width is not None:
        if target_width < min_size or target_width > max_size:
            raise ValueError(
                f"目标宽度必须在 [{min_size}, {max_size}] 范围内，当前值: {target_width}"
            )

    if target_height is not None:
        if target_height < min_size or target_height > max_size:
            raise ValueError(
                f"目标高度必须在 [{min_size}, {max_size}] 范围内，当前值: {target_height}"
            )

    # 计算新尺寸
    if target_width and target_height:
        new_width = target_width
        new_height = target_height
    elif target_width:
        # 按比例缩放
        ratio = target_width / original_width
        new_width = target_width
        new_height = int(original_height * ratio)
    elif target_height:
        # 按比例缩放
        ratio = target_height / original_height
        new_width = int(original_width * ratio)
        new_height = target_height
    else:
        # 自动调整以满足范围要求
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

    # 确保在范围内
    new_width = max(min_size, min(max_size, new_width))
    new_height = max(min_size, min(max_size, new_height))

    # 无需调整
    if (new_width, new_height) == (original_width, original_height):
        return str(image_path)

    # 调整并保存
    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    output_path = image_path.parent / f"resized_{image_path.name}"
    resized_img.save(output_path, quality=95)

    return str(output_path)


def prepare_image_url(image_path: str | Path) -> str:
    """
    将本地图片路径转换为 VideoSynthesis 可接受的 file:// URL

    参数:
    - image_path: 图片路径

    返回:
    - file:// URL 格式的字符串
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    # 使用绝对路径
    absolute_path = image_path.absolute()
    return f"file://{absolute_path}"


def resolve_image_url(image_source: str | Path, image_store=None) -> str | None:
    """
    从多种来源解析图片 URL，返回 VideoSynthesis 可接受的 URL 格式。

    支持的输入格式：
    - data:image/...;base64,... URI（直接返回）
    - http:// 或 https:// 网络图片 URL（直接返回）
    - file:// 本地文件路径
    - 本地文件路径（转换为 file:// URL）

    返回格式：
    - file:// 本地文件路径
    - http:// 或 https:// 网络图片
    - data:image/...;base64,... data URI

    参数:
    - image_source: 图片来源（URL 或路径）
    - image_store: 已废弃，保留仅为兼容性

    返回:
    - 解析后的 URL，失败返回 None
    """
    if not image_source:
        return None

    source = str(image_source)

    # 处理 data URI - 直接返回
    if source.startswith("data:"):
        if ";base64," in source:
            return source
        else:
            # 不支持非 base64 的 data URI
            import logging

            logging.getLogger(__name__).warning(
                f"不支持的 data URI 格式（非 base64）: {source[:50]}..."
            )
            return None

    # 处理 HTTP/HTTPS URL - 直接返回
    if source.startswith(("http://", "https://")):
        return source

    # 处理 file:// URL - 直接返回
    if source.startswith("file://"):
        return source

    # 尝试作为本地路径
    candidate = Path(source)
    if candidate.exists():
        # 转换为 file:// URL
        return f"file://{candidate.absolute()}"

    # 未知格式
    import logging

    logging.getLogger(__name__).warning(f"无法识别的图片源格式: {source[:100]}...")
    return None
    candidate = Path(source)
    if candidate.exists():
        # 转换为 file:// URL
        return f"file://{candidate.absolute()}"

    # 未知格式
    import logging

    logging.getLogger(__name__).warning(f"无法识别的图片源格式: {source[:100]}...")
    return None


# ========== 任务轮询工具 ==========


class TaskPoller:
    """
    通用任务轮询器，用于 DashScope 异步任务

    用法:
        poller = TaskPoller(api_key="your_key", interval=5.0, timeout=600)
        result = poller.poll(task_id)
    """

    def __init__(
        self,
        api_key: str,
        interval: float = 5.0,
        timeout: float = 600.0,
        verbose: bool = True,
    ):
        """
        初始化任务轮询器

        参数:
        - api_key: DashScope API 密钥
        - interval: 轮询间隔（秒），默认 5 秒
        - timeout: 超时时间（秒），默认 600 秒（10 分钟）
        - verbose: 是否显示详细进度，默认 True
        """
        self.api_key = api_key
        self.interval = interval
        self.timeout = timeout
        self.verbose = verbose

    def poll(self, task_id: str) -> Dict[str, Any]:
        """
        轮询任务状态直到完成或超时

        参数:
        - task_id: 任务 ID

        返回:
        - 包含任务结果的字典

        异常:
        - TimeoutError: 任务超时
        - RuntimeError: 任务失败
        """
        if self.verbose:
            print(f"\n⏳ 开始轮询任务: {task_id}")
            print(f"   轮询间隔: {self.interval}秒")
            print(f"   超时时间: {self.timeout}秒")

        start_time = time.time()
        attempts = 0

        while True:
            attempts += 1
            elapsed = time.time() - start_time

            # 检查超时
            if elapsed > self.timeout:
                raise TimeoutError(f"任务 {task_id} 超时（已等待 {elapsed:.1f} 秒）")

            # 查询任务状态
            response = VideoSynthesis.fetch(
                api_key=self.api_key,
                task=task_id,
            )

            if response.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"查询任务状态失败: status_code={response.status_code}, "
                    f"code={response.code}, message={response.message}"
                )

            status = response.output.task_status

            if self.verbose:
                self._print_progress(attempts, elapsed, status)

            # 检查任务状态
            if status == "SUCCEEDED":
                if self.verbose:
                    print("\n✓ 任务完成！")
                return self._build_result(response)

            elif status == "FAILED":
                error_msg = getattr(response.output, "message", "未知错误")
                raise RuntimeError(f"任务失败: {error_msg}")

            elif status in ("PENDING", "RUNNING"):
                time.sleep(self.interval)

            else:
                if self.verbose:
                    print(f"⚠️  警告: 未知任务状态 '{status}'，继续轮询...")
                time.sleep(self.interval)

    def _print_progress(
        self,
        attempts: int,
        elapsed: float,
        status: str,
    ) -> None:
        """打印轮询进度"""
        status_icons = {
            "PENDING": "⏸️",
            "RUNNING": "▶️",
            "SUCCEEDED": "✅",
            "FAILED": "❌",
        }
        icon = status_icons.get(status, "❓")

        print(
            f"\r   [{icon}] 第 {attempts} 次查询 | "
            f"已等待 {elapsed:.1f}秒 | "
            f"状态: {status}",
            end="",
            flush=True,
        )

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

        # 添加用量信息
        if usage:
            result["usage"] = {
                "video_count": getattr(usage, "video_count", 0),
            }

        return result


# ========== 视频下载工具 ==========


def download_video(
    video_url: str,
    output_path: str | Path | None = None,
    show_progress: bool = True,
) -> str:
    """
    下载视频文件并显示进度

    参数:
    - video_url: 视频URL
    - output_path: 保存路径（可选，默认使用时间戳命名）
    - show_progress: 是否显示下载进度，默认 True

    返回:
    - 保存的文件路径
    """
    import requests

    # 如果未指定输出路径，使用时间戳生成文件名
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"video_{timestamp}.mp4")
    else:
        output_path = Path(output_path)

    # 确保输出目录存在
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if show_progress:
        print("\n📦 正在下载视频...")
        print(f"   保存路径: {output_path}")

    try:
        # 发送请求，启用流式下载
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        # 获取文件总大小
        total_size = int(response.headers.get("content-length", 0))
        block_size = 8192  # 8KB
        downloaded_size = 0

        # 开始下载
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # 显示进度
                    if show_progress and total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        downloaded_mb = downloaded_size / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        print(
                            f"\r   进度: {progress:.1f}% "
                            f"({downloaded_mb:.2f}MB / {total_mb:.2f}MB)",
                            end="",
                            flush=True,
                        )

        if show_progress:
            print()  # 换行
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print("✓ 视频下载完成！")
            print(f"   文件大小: {file_size_mb:.2f} MB")
            print(f"   保存位置: {output_path.absolute()}")

        return str(output_path)

    except Exception as e:
        # 如果下载失败，删除不完整的文件
        if output_path.exists():
            output_path.unlink()
        raise RuntimeError(f"视频下载失败: {e}") from e


__all__ = [
    "resize_image_with_constraints",
    "prepare_image_url",
    "resolve_image_url",
    "TaskPoller",
    "download_video",
]
