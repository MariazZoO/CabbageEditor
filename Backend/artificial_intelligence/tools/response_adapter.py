from __future__ import annotations

import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, List

from Backend.artificial_intelligence.service.context import get_current_session

# 定义上下文变量，用于在工具调用链中隐式传递配置
_interface_type_ctx = ContextVar("interface_type", default=None)
_session_id_ctx = ContextVar("session_id", default=None)


@contextmanager
def tool_context(interface_type: str | None = None, session_id: str | None = None):
    """
    工具执行上下文管理器。
    在调用工具前设置此上下文，工具内部即可自动获取 interface_type 和 session_id。
    
    Usage:
        with tool_context(interface_type="integrated", session_id="123"):
            result = tool_func(...)
    """
    tokens = {}
    if interface_type is not None:
        tokens[_interface_type_ctx] = _interface_type_ctx.set(interface_type)
    if session_id is not None:
        tokens[_session_id_ctx] = _session_id_ctx.set(session_id)
    
    try:
        yield
    finally:
        for ctx, token in tokens.items():
            ctx.reset(token)


def build_part(
    *,
    content_type: str,
    content_text: str | None = None,
    content_url: str | None = None,
    url_expire_time: int | None = None,
    parameter: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """构建单个 part 结构"""
    part: Dict[str, Any] = {
        "content_type": content_type,
    }
    if content_text is not None:
        part["content_text"] = content_text
    if content_url is not None:
        part["content_url"] = content_url
    if url_expire_time is not None:
        part["url_expire_time"] = url_expire_time
    if parameter:
        filtered_parameter = {k: v for k, v in parameter.items() if v is not None}
        if filtered_parameter:
            part["parameter"] = filtered_parameter
    return part


class ToolResult:
    """工具内部返回结构"""

    def __init__(
        self,
        *,
        parts: List[Dict[str, Any]],
        metadata: Dict[str, Any] | None = None,
        error_code: int = 0,
        status_info: str = "success",
    ):
        self.parts = parts
        self.metadata = metadata or {}
        self.error_code = error_code
        self.status_info = status_info

    def to_dict(
        self,
        interface_type: str | None = None,
        session_id: str | None = None,
        role: str = "tools",
    ) -> Dict[str, Any]:
        """
        转换为字典对象（不进行 JSON 序列化）。
        优先使用上下文中的值，其次使用传入参数。
        """
        # 1. 确定 interface_type
        # 优先使用 Context (Agent 强制覆盖)，其次是参数 (工具默认)，最后报错
        final_interface_type = _interface_type_ctx.get() or interface_type
        if final_interface_type is None:
            # 如果既没有传参也没有上下文，为了兼容性暂时允许，但在严格模式下应报错
            # 这里抛出异常以强制规范化
            raise ValueError(
                "interface_type is missing. Please provide it via argument or use 'with tool_context(...):'"
            )

        # 2. 确定 session_id
        sid = _session_id_ctx.get() or session_id or get_current_session()
        sent_time = int(time.time() * 1000)

        return {
            "session_id": sid,
            "error_code": self.error_code,
            "status_info": self.status_info,
            "llm_content": [
                {
                    "role": role,
                    "interface_type": final_interface_type,
                    "sent_time_stamp": sent_time,
                    "part": self.parts,
                }
            ],
            "metadata": self.metadata,
        }

    def to_envelope(
        self,
        interface_type: str | None = None,
        session_id: str | None = None,
        role: str = "tools",
    ) -> str:
        """
        转换为最终 envelope JSON 字符串。
        注意：如果追求性能，建议直接使用 to_dict() 获取对象，避免重复序列化。
        """
        data = self.to_dict(interface_type=interface_type, session_id=session_id, role=role)
        return json.dumps(data, ensure_ascii=False)


def build_success_result(
    *,
    parts: List[Dict[str, Any]],
    metadata: Dict[str, Any] | None = None,
) -> ToolResult:
    """构建成功的工具结果"""
    return ToolResult(parts=parts, metadata=metadata, error_code=0, status_info="success")


def build_error_result(
    *,
    error_message: str,
    error_code: int = 1,
    metadata: Dict[str, Any] | None = None,
) -> ToolResult:
    """构建错误的工具结果"""
    return ToolResult(
        parts=[build_part(content_type="text", content_text=error_message)],
        metadata=metadata,
        error_code=error_code,
        status_info=error_message,
    )


# 兼容旧接口：直接构建最终 JSON（用于独立接口调用）
def build_llm_tool_response(
    *,
    interface_type: str | None = None,
    parts: List[Dict[str, Any]],
    error_code: int = 0,
    status_info: str = "success",
    role: str = "tools",
    metadata: Dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    """直接构建最终 envelope"""
    result = ToolResult(
        parts=parts, metadata=metadata, error_code=error_code, status_info=status_info
    )
    return result.to_envelope(interface_type=interface_type, session_id=session_id, role=role)


def build_error_response(
    *,
    error_message: str,
    interface_type: str | None = None,
    error_code: int = 1,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """直接构建错误 envelope"""
    result = build_error_result(error_message=error_message, error_code=error_code, metadata=metadata)
    return result.to_envelope(interface_type=interface_type)


__all__ = [
    "tool_context",
    "build_part",
    "ToolResult",
    "build_success_result",
    "build_error_result",
    "build_llm_tool_response",
    "build_error_response",
]
