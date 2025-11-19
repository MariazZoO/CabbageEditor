from __future__ import annotations
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal, Slot, QTimer

from Backend.artificial_intelligence.service import handle_user_message
from Backend.artificial_intelligence.config.config import get_app_config

from Backend.artificial_intelligence.service import handle_user_message
from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.models import get_chat_model
from Backend.utils.logging import get_logger

logger = get_logger(__name__)


def _format_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        parts = [_format_exception(sub) for sub in exc.exceptions]
        return "; ".join(filter(None, parts))
    return str(exc) or exc.__class__.__name__


def _warmup_llm_connection() -> None:
    """后台线程执行最小 LLM 请求，提前建立连接。"""
    try:
        cfg = get_ai_config()
        chat_cfg = cfg.chat
        llm = get_chat_model(
            cfg,
            provider_name=chat_cfg.provider,
            model_name=chat_cfg.model,
            temperature=chat_cfg.temperature,
            request_timeout=chat_cfg.request_timeout,
        )
        warmup_prompt = [
            {"role": "system", "content": "预热：请忽略此消息。"},
            {"role": "user", "content": "ping"},
        ]
        llm.invoke(warmup_prompt)
        logger.debug("LLM warmup completed")
    except Exception as exc:
        logger.debug("LLM warmup skipped: %s", exc)


class AIService(QObject):
    ai_response = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # LangChain agent 在后台线程里运行，避免阻塞 UI 事件循环
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AI_")
        # 创建一个新的事件循环用于协程
        self._loop = asyncio.new_event_loop()
        # 跟踪活动的任务
        self._active_tasks: set[asyncio.Task] = set()

        # 使用 QTimer 定期处理事件循环，确保协程能运行
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_event_loop)
        self._timer.start(10)  # 每 10ms 处理一次事件循环

        # 预热 LLM 连接，避免首轮对话长时间握手
        self._executor.submit(_warmup_llm_connection)

    def _process_event_loop(self) -> None:
        """处理 asyncio 事件循环（由 QTimer 定期调用）"""
        try:
            # 运行所有准备好的回调，但不阻塞
            self._loop.call_soon(self._loop.stop)
            self._loop.run_forever()
        except Exception as e:
            logger.exception(f"事件循环处理错误：{e}")

    @Slot(str)
    def send_message_to_ai(self, ai_message: str) -> None:
        """
        发送消息到 AI（使用协程异步处理）

        前端消息格式:
        {
            "message": "用户文本",
            "session_id": "session_xxx",
            "images": [
                {"url": "https://...", "type": "product"},
                {"data": "base64...", "type": "scene"}
            ]
        }
        """
        task = self._loop.create_task(self._process_ai_message(ai_message))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _process_ai_message(self, ai_message: str) -> None:
        """协程：处理 AI 消息"""
        try:
            msg_data = json.loads(ai_message)
            payload = msg_data if isinstance(msg_data, dict) else {"message": msg_data}

            # 在线程池中执行阻塞的 AI 调用
            result = await self._loop.run_in_executor(
                self._executor, handle_user_message, payload
            )

            # 发送响应信号
            self.ai_response.emit(result)

        except BaseException as exc:
            error_payload = json.dumps(
                {
                    "type": "error",
                    "content": _format_exception(exc),
                    "status": "error",
                    "timestamp": int(time.time()),
                }
            )
            self.ai_response.emit(error_payload)

    @Slot(str)
    def upload_image(self, payload: str) -> None:
        """
        上传图片

        前端消息格式:
        {
            "data": "base64...",
            "name": "image.png",
            "type": "product",  // category: product | scene
            "session_id": "session_xxx",
            "token": "token_xxx"
        }
        """
        task = self._loop.create_task(self._process_image_upload(payload))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _process_image_upload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {}
        try:
            result = await self._loop.run_in_executor(
                self._executor, data
            )
            self.ai_response.emit(result)
        except BaseException as exc:
            error_payload = json.dumps(
                {
                    "type": "image_upload",
                    "status": "error",
                    "token": data.get("token"),
                    "content": _format_exception(exc),
                    "timestamp": int(time.time()),
                }
            )
            self.ai_response.emit(error_payload)

    def cleanup(self):
        """清理资源（在 service 销毁前调用）"""
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
            except Exception:
                pass

        self._active_tasks.clear()

        # 关闭线程池
        self._executor.shutdown(wait=True, cancel_futures=True)

        # 关闭事件循环
        try:
            self._loop.close()
        except Exception:
            pass
