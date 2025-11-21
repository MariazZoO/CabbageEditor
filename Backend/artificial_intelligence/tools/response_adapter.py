from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from Backend.artificial_intelligence.tools.session import get_current_session


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
    """工具内部返回结构（不含 interface_type，由调用层指定）"""

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

    def to_envelope(
        self,
        interface_type: str,
        session_id: str | None = None,
        role: str = "tools",
    ) -> str:
        """转换为最终 envelope JSON，由调用层指定 interface_type"""
        sid = session_id or get_current_session()
        sent_time = int(time.time() * 1000)
        envelope = {
            "session_id": sid,
            "error_code": self.error_code,
            "status_info": self.status_info,
            "llm_content": [
                {
                    "role": role,
                    "interface_type": interface_type,
                    "sent_time_stamp": sent_time,
                    "part": self.parts,
                }
            ],
            "metadata": self.metadata,
        }
        return json.dumps(envelope, ensure_ascii=False)


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
    interface_type: str,
    parts: List[Dict[str, Any]],
    error_code: int = 0,
    status_info: str = "success",
    role: str = "tools",
    metadata: Dict[str, Any] | None = None,
    session_id: str | None = None,
) -> str:
    """直接构建最终 envelope（独立接口使用）"""
    result = ToolResult(
        parts=parts, metadata=metadata, error_code=error_code, status_info=status_info
    )
    return result.to_envelope(interface_type=interface_type, session_id=session_id, role=role)


def build_error_response(
    *,
    interface_type: str,
    error_message: str,
    error_code: int = 1,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """直接构建错误 envelope（独立接口使用）"""
    result = build_error_result(error_message=error_message, error_code=error_code, metadata=metadata)
    return result.to_envelope(interface_type=interface_type)


__all__ = [
    "build_part",
    "ToolResult",
    "build_success_result",
    "build_error_result",
    "build_llm_tool_response",
    "build_error_response",
]
