"""
Models 模块通用工具集
提供图片处理、重试机制、任务轮询等功能
"""

from __future__ import annotations

import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, Tuple, Optional
import logging

from PIL import Image

from Backend.artificial_intelligence.config.ai_config import ProviderConfig


# ========== 通用客户端基类 ==========


class BaseAPIClient:
    """通用 API 客户端基类"""

    def __init__(self, provider: ProviderConfig, base_url: str | None = None):
        if not provider.api_key:
            raise RuntimeError(f"Provider '{provider.name}' 缺少 API Key。")
        self.provider = provider
        self.api_key = provider.api_key
        # 优先使用传入的 base_url，其次是 provider 配置的，最后为空字符串
        self.base_url = (base_url or provider.base_url or "").rstrip("/")
        self.headers = {
            **(provider.headers or {}),
            "Authorization": f"Bearer {self.api_key}",
        }


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

    Args:
        image_path: 图片路径
        target_width: 目标宽度（可选）
        target_height: 目标高度（可选）
        max_size: 最大尺寸，默认 2000
        min_size: 最小尺寸，默认 360

    Returns:
        调整后的图片路径（如果无需调整则返回原路径）
    """
    image_path = Path(image_path)
    img = Image.open(image_path)
    w, h = img.size

    # 验证参数
    for val, name in [(target_width, "宽度"), (target_height, "高度")]:
        if val is not None and not (min_size <= val <= max_size):
            raise ValueError(f"目标{name}必须在 [{min_size}, {max_size}] 范围内")

    # 计算新尺寸
    if target_width and target_height:
        new_w, new_h = target_width, target_height
    elif target_width:
        new_w = target_width
        new_h = int(h * (target_width / w))
    elif target_height:
        new_h = target_height
        new_w = int(w * (target_height / h))
    else:
        new_w, new_h = w, h
        # 缩小过大的图片
        if max(new_w, new_h) > max_size:
            scale = max_size / max(new_w, new_h)
            new_w, new_h = int(new_w * scale), int(new_h * scale)
        # 放大过小的图片
        if min(new_w, new_h) < min_size:
            scale = min_size / min(new_w, new_h)
            new_w, new_h = int(new_w * scale), int(new_h * scale)

    # 最终强制限制（防止极端比例导致的越界）
    new_w = max(min_size, min(max_size, new_w))
    new_h = max(min_size, min(max_size, new_h))

    if (new_w, new_h) == (w, h):
        return str(image_path)

    output_path = image_path.parent / f"resized_{image_path.name}"
    img.resize((new_w, new_h), Image.Resampling.LANCZOS).save(output_path, quality=95)
    return str(output_path)


# ========== 重试工具 ==========


T = TypeVar("T")


def retry_operation(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
        exceptions: 需要捕获的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            current_delay = delay
            last_exception = None

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    retries += 1
                    if retries > max_retries:
                        break

                    logging.getLogger(__name__).warning(
                        f"操作失败，正在重试 ({retries}/{max_retries}): {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            if last_exception:
                raise last_exception
            raise RuntimeError("重试失败但未捕获到异常")

        return wrapper

    return decorator


# ========== 视频任务轮询 ==========


class TaskPoller:
    """
    通用异步任务轮询器

    用法:
        poller = TaskPoller(interval=5.0, timeout=600)
        result = poller.poll(task_id, check_status_func)
    """

    def __init__(
        self,
        interval: float = 5.0,
        timeout: float = 600.0,
        verbose: bool = True,
    ):
        """
        初始化任务轮询器

        Args:
            interval: 轮询间隔（秒），默认 5 秒
            timeout: 超时时间（秒），默认 600 秒（10 分钟）
            verbose: 是否显示详细进度，默认 True
        """
        self.interval = interval
        self.timeout = timeout
        self.verbose = verbose

    def poll(
        self,
        task_id: str,
        check_status: Callable[[str], Tuple[str, Any, Optional[str]]],
    ) -> Any:
        """
        轮询任务状态直到完成或超时

        Args:
            task_id: 任务 ID
            check_status: 检查状态的回调函数
                参数: task_id
                返回: (status, result, error_msg)
                status 必须是: "PENDING", "RUNNING", "SUCCEEDED", "FAILED" 之一

        Returns:
            任务结果 (result)

        Raises:
            TimeoutError: 任务超时
            RuntimeError: 任务失败
        """
        if self.verbose:
            print(f"\n[INFO] 开始轮询任务: {task_id}")
            print(f"   轮询间隔: {self.interval}秒")
            print(f"   超时时间: {self.timeout}秒")

        start_time = time.time()
        attempts = 0

        while True:
            attempts += 1
            elapsed = time.time() - start_time

            if elapsed > self.timeout:
                raise TimeoutError(f"任务 {task_id} 超时（已等待 {elapsed:.1f} 秒）")

            try:
                status, result, error_msg = check_status(task_id)
            except Exception as e:
                # 检查状态本身出错，视为任务失败或临时错误？
                # 这里假设是临时错误，打印警告并重试，或者直接抛出？
                # 为了稳健性，如果是网络错误等，应该重试。
                # 这里简单处理：如果 check_status 抛出异常，视为查询失败，继续轮询
                if self.verbose:
                    print(f"[WARN] 查询状态异常: {e}，继续轮询...")
                time.sleep(self.interval)
                continue

            if self.verbose:
                self._print_progress(attempts, elapsed, status)

            if status == "SUCCEEDED":
                if self.verbose:
                    print("\n[SUCCESS] 任务完成！")
                return result

            elif status == "FAILED":
                msg = error_msg or "未知错误"
                raise RuntimeError(f"任务失败: {msg}")

            elif status in ("PENDING", "RUNNING", "PROCESSING"):  # 兼容 PROCESSING
                time.sleep(self.interval)

            else:
                if self.verbose:
                    print(f"[WARN] 警告: 未知任务状态 '{status}'，继续轮询...")
                time.sleep(self.interval)

    def _print_progress(self, attempts: int, elapsed: float, status: str) -> None:
        """打印轮询进度"""
        status_icons = {
            "PENDING": "[WAIT]",
            "RUNNING": "[RUN]",
            "PROCESSING": "[PROC]",
            "SUCCEEDED": "[OK]",
            "FAILED": "[FAIL]",
        }
        icon = status_icons.get(status, "[?]")

        print(
            f"\r   {icon} 第 {attempts} 次查询 | " f"已等待 {elapsed:.1f}秒 | " f"状态: {status} ",
            end="",
            flush=True,
        )


__all__ = [
    "BaseAPIClient",
    "resize_image_with_constraints",
    "retry_operation",
    "TaskPoller",
]
