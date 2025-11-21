from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional

from Backend.artificial_intelligence.agent.conversation import default_session_id
from Backend.artificial_intelligence.tools.session import (
    reset_current_session,
    set_current_session,
)


def ensure_dict(payload: Any) -> Dict[str, Any]:
    """确保 payload 为字典，非字典时返回空字典。"""
    return payload if isinstance(payload, dict) else {}


def require_fields(data: Dict[str, Any], fields: Iterable[str]) -> None:
    """验证必填字段存在且非空。"""
    missing = [name for name in fields if not data.get(name)]
    if missing:
        raise ValueError(f"缺少必需参数: {', '.join(missing)}")


@contextmanager
def session_context(session_id: Optional[str] = None):
    """统一管理会话上下文，保证 set/reset 成对调用。"""
    sid = session_id or default_session_id()
    token = set_current_session(sid)
    try:
        yield sid
    finally:
        reset_current_session(token)


def pick_tool(tools: List[Any], names: Iterable[str]) -> Any:
    """按候选名称顺序选择工具。"""
    for name in names:
        for tool in tools:
            if tool.name == name:
                return tool
    raise RuntimeError(f"未找到匹配的工具: {', '.join(names)}")


def build_success_response(
    interface_type: str,
    session_id: str,
    metadata: Dict[str, Any] | None = None,
    parts: List[Dict[str, Any]] | None = None,
    role: str = "assistant",
    llm_content: List[Dict[str, Any]] | None = None,
) -> str:
    """构造成功响应结构。

    顶层: session_id, error_code(0), status_info("ok"), llm_content(list), metadata(dict)
    第二层: role, interface_type, sent_time_stamp(int), part(list)
    第三层: part 元素包含 content_type / content_text|content_url / 可选 parameter(dict)
    """
    if llm_content is None:
        if parts is None:
            parts = []
        llm_content = [
            {
                "role": role,
                "interface_type": interface_type,
                "sent_time_stamp": int(time.time()),
                "part": parts,
            }
        ]

    body: Dict[str, Any] = {
        "session_id": session_id,
        "error_code": 0,
        "status_info": "ok",
        "llm_content": llm_content,
        "metadata": metadata or {},
    }
    return json.dumps(body, ensure_ascii=False)


def build_error_response(
    interface_type: str,
    session_id: str | None,
    exc: Exception,
    metadata: Dict[str, Any] | None = None,
    role: str = "assistant",
) -> str:
    """构造错误响应结构。

    错误响应也应该符合三层结构：
    - 顶层: error_code=1, status_info=错误信息
    - 第二层: llm_content 包含一个表示错误的消息
    - 第三层: part 包含错误详情的文本
    """
    error_message = str(exc)
    exception_type = type(exc).__name__

    body: Dict[str, Any] = {
        "session_id": session_id or default_session_id(),
        "error_code": 1,
        "status_info": error_message,
        "llm_content": [
            {
                "role": role,
                "interface_type": interface_type,
                "sent_time_stamp": int(time.time()),
                "part": [
                    {
                        "content_type": "text",
                        "content_text": error_message,
                        "parameter": {
                            "error": True,
                            "exception_type": exception_type,
                        },
                    }
                ],
            }
        ],
        "metadata": metadata or {},
    }
    return json.dumps(body, ensure_ascii=False)


__all__ = [
    "ensure_dict",
    "require_fields",
    "session_context",
    "pick_tool",
    "build_success_response",
    "build_error_response",
]
