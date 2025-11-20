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
    """构造统一的 JSON 响应。"""
    body: Dict[str, Any] = {
        "type": response_type,
        "status": status,
        "timestamp": int(time.time()),
        "session_id": session_id or default_session_id(),
    }
    body.update(kwargs)
    return json.dumps(body, ensure_ascii=False)


def make_error(response_type: str, session_id: Optional[str], exc: Exception) -> str:
    """构造统一的错误响应。"""
    return make_response(
        response_type=response_type,
        status="error",
        session_id=session_id,
        content=str(exc),
    )


__all__ = [
    "ensure_dict",
    "require_fields",
    "session_context",
    "pick_tool",
    "make_response",
    "make_error",
]
