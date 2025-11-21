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


def make_response(
    response_type: str,
    status: str = "success",
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """原始（旧格式）响应构造，保留兼容。"""
    body: Dict[str, Any] = {
        "type": response_type,
        "status": status,
        "timestamp": int(time.time()),
        "session_id": session_id or default_session_id(),
    }
    body.update(kwargs)
    return json.dumps(body, ensure_ascii=False)


def make_error(response_type: str, session_id: Optional[str], exc: Exception) -> str:
    """旧格式错误响应。"""
    return make_response(
        response_type=response_type,
        status="error",
        session_id=session_id,
        content=str(exc),
    )


def build_multilayer_success(
    interface_type: str,
    session_id: str,
    metadata: Dict[str, Any],
    parts: List[Dict[str, Any]],
    role: str = "assistant",
) -> str:
    """构造三层成功结构，匹配 tests 期望。

    顶层: session_id, error_code(0), status_info("ok"), llm_content(list), metadata(dict)
    第二层: role, interface_type, sent_time_stamp(int), part(list)
    第三层: part 元素包含 content_type / content_text|content_url / 可选 parameter(dict)
    """
    body: Dict[str, Any] = {
        "session_id": session_id,
        "error_code": 0,
        "status_info": "ok",
        "llm_content": [
            {
                "role": role,
                "interface_type": interface_type,
                "sent_time_stamp": int(time.time()),
                "part": parts,
            }
        ],
        "metadata": metadata or {},
    }
    return json.dumps(body, ensure_ascii=False)


def build_multilayer_error(
    interface_type: str,
    session_id: str,
    metadata: Dict[str, Any],
    exc: Exception,
    role: str = "assistant",
) -> str:
    """构造三层错误结构，包含完整的 llm_content。

    错误响应也应该符合三层结构：
    - 顶层: error_code=1, status_info=错误信息
    - 第二层: llm_content 包含一个表示错误的消息
    - 第三层: part 包含错误详情的文本
    """
    error_message = str(exc)
    exception_type = type(exc).__name__

    body: Dict[str, Any] = {
        "session_id": session_id,
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
    "make_response",
    "make_error",
    "build_multilayer_success",
    "build_multilayer_error",
]
