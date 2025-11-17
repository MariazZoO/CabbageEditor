from __future__ import annotations
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from Backend.utils.bootstrap import bootstrap
from Backend.artificial_intelligence.service import handle_image_generation
from Backend.utils.logging import get_logger

bootstrap()
logger = get_logger(__name__)


def _format_exception(exc: BaseException) -> str:
    """格式化异常信息"""
    if isinstance(exc, BaseExceptionGroup):
        parts = [_format_exception(sub) for sub in exc.exceptions]
        return "; ".join(filter(None, parts))
    return str(exc) or exc.__class__.__name__


class ImageGenerationService(QObject):
    """
    独立的图像生成服务

    使用协程和线程池机制处理图像生成请求，避免阻塞 UI 线程
    """

    # 图像生成响应信号
    image_generation_response = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # 专门用于图像生成的线程池
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="ImageGen_"
        )

        # 创建独立的事件循环用于协程
        self._loop = asyncio.new_event_loop()

        # 跟踪活动的任务
        self._active_tasks: set[asyncio.Task] = set()

        # 使用 QTimer 定期处理事件循环
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_event_loop)
        self._timer.start(10)  # 每 10ms 处理一次

        logger.info("ImageGenerationService initialized")

    def _process_event_loop(self) -> None:
        """处理 asyncio 事件循环（由 QTimer 定期调用）"""
        try:
            # 运行所有准备好的回调，但不阻塞
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()
        except Exception as e:
            logger.exception(f"图像生成服务事件循环处理错误：{e}")

    @Slot(str)
    def generate_image(self, payload: str) -> None:
        """
        生成图像（槽函数）

        前端消息格式:
        {
            "prompt": "生成图像的提示词",
            "session_id": "session_xxx",
            "product_url": "autosave://...",  // 可选：产品图片URL
            "scene_url": "autosave://...",    // 可选：场景图片URL
            "use_references": false           // 可选：是否自动引用会话中的图片
        }

        响应格式（成功）:
        {
            "type": "image_generation",
            "status": "success",
            "timestamp": 1700000000,
            "session_id": "session_xxx",
            "prompt": "提示词",
            "image": {
                "name": "generated_xxx.png",
                "path": "/path/to/image",
                "url": "autosave://...",
                "base64": "base64编码的图像数据"
            }
        }

        响应格式（失败）:
        {
            "type": "image_generation",
            "status": "error",
            "timestamp": 1700000000,
            "session_id": "session_xxx",
            "content": "错误信息"
        }
        """
        task = self._loop.create_task(self._process_image_generation(payload))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _process_image_generation(self, payload: str) -> None:
        """协程：处理图像生成请求"""
        data = {}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"图像生成请求 JSON 解析失败: {e}")
            error_payload = json.dumps(
                {
                    "type": "image_generation",
                    "status": "error",
                    "content": f"无效的 JSON 格式: {str(e)}",
                    "timestamp": int(time.time()),
                }
            )
            self.image_generation_response.emit(error_payload)
            return

        try:
            # 在线程池中执行阻塞的图像生成操作
            result = await self._loop.run_in_executor(
                self._executor, handle_image_generation, data
            )

            # 发送响应信号
            self.image_generation_response.emit(result)
            logger.debug(f"图像生成成功，session: {data.get('session_id')}")

        except BaseException as exc:
            logger.exception(f"图像生成失败: {exc}")
            error_payload = json.dumps(
                {
                    "type": "image_generation",
                    "status": "error",
                    "session_id": data.get("session_id"),
                    "content": _format_exception(exc),
                    "timestamp": int(time.time()),
                }
            )
            self.image_generation_response.emit(error_payload)

    def cleanup(self) -> None:
        """
        清理资源（在服务销毁前调用）

        执行步骤：
        1. 停止定时器
        2. 取消所有活动的任务
        3. 等待任务完成或取消
        4. 关闭线程池
        5. 关闭事件循环
        """
        logger.info("Cleaning up ImageGenerationService...")

        # 停止定时器
        if self._timer.isActive():
            self._timer.stop()

        # 取消所有活动的任务
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()

        # 等待所有任务完成或取消
        if self._active_tasks:
            try:
                self._loop.run_until_complete(
                    asyncio.gather(*self._active_tasks, return_exceptions=True)
                )
            except Exception as e:
                logger.warning(f"任务清理时出现异常: {e}")

        self._active_tasks.clear()

        # 关闭线程池
        try:
            self._executor.shutdown(wait=True, cancel_futures=True)
        except Exception as e:
            logger.warning(f"线程池关闭时出现异常: {e}")

        # 关闭事件循环
        try:
            self._loop.close()
        except Exception as e:
            logger.warning(f"事件循环关闭时出现异常: {e}")

        logger.info("ImageGenerationService cleanup completed")


__all__ = ["ImageGenerationService"]
