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
    interface_type: str,
    session_id: Optional[str] = None,
    role: str = "assistant",
    parts: Optional[List[Dict[str, Any]]] = None,
    error_code: int = 0,
    status_info: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """构造统一的 JSON 响应。"""
    if parts is None:
        parts = []

    body: Dict[str, Any] = {
        "session_id": session_id or default_session_id(),
        "error_code": error_code,
        "status_info": status_info,
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


def make_error(interface_type: str, session_id: Optional[str], exc: Exception) -> str:
    """构造统一的错误响应。"""
    return make_response(
        interface_type=interface_type,
        session_id=session_id,
        error_code=1,
        status_info=str(exc),
    )


def extract_latest_user_content(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """从 payload 中提取最新的用户消息内容。"""
    llm_content = payload.get("llm_content", [])
    if not isinstance(llm_content, list):
        return None

    # 倒序查找最后一个 user 消息
    for content in reversed(llm_content):
        if content.get("role") == "user":
            return content
    return None


def extract_parameter(
    payload: Dict[str, Any], param_name: str, default: Any = None
) -> Any:
    """尝试从 payload 的各个层级提取参数。"""
    # 1. 尝试从 metadata 提取
    metadata = payload.get("metadata", {})
    if param_name in metadata:
        return metadata[param_name]

    # 2. 尝试从最新的 user content 的 parameter 提取
    user_content = extract_latest_user_content(payload)
    if user_content:
        parts = user_content.get("part", [])
        for part in parts:
            params = part.get("parameter", {})
            if param_name in params:
                return params[param_name]
            # 同时也尝试从 part 直接提取 (兼容旧逻辑或简化逻辑)
            if param_name in part:
                return part[param_name]

    # 3. 尝试从 payload 顶层提取 (兼容旧逻辑)
    if param_name in payload:
        return payload[param_name]

    return default


__all__ = [
    "ensure_dict",
    "require_fields",
    "session_context",
    "pick_tool",
    "make_response",
    "make_error",
    "extract_latest_user_content",
    "extract_parameter",
]
