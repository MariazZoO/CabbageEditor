"""
视频生成任务轮询器
用于异步任务状态轮询和结果获取
"""

from http import HTTPStatus
import time
from typing import Any, Dict
from dashscope import VideoSynthesis


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
    ):
        """
        初始化任务轮询器

        参数:
        - api_key: DashScope API 密钥
        - interval: 轮询间隔（秒），默认 5 秒
        - timeout: 超时时间（秒），默认 600 秒（10 分钟）
        """
        self.api_key = api_key
        self.interval = interval
        self.timeout = timeout

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
                task_id=task_id,
            )

            if response.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"查询任务状态失败: status_code={response.status_code}, "
                    f"code={response.code}, message={response.message}"
                )

            status = response.output.task_status
            self._print_progress(attempts, elapsed, status)

            # 检查任务状态
            if status == "SUCCEEDED":
                print("\n✓ 任务完成！")
                return self._build_result(response)

            elif status == "FAILED":
                error_msg = getattr(response.output, "message", "未知错误")
                raise RuntimeError(f"任务失败: {error_msg}")

            elif status in ("PENDING", "RUNNING"):
                # 任务进行中，继续轮询
                time.sleep(self.interval)

            else:
                # 未知状态
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
                "image_count": getattr(usage, "image_count", 0),
            }

        return result


__all__ = ["TaskPoller"]
