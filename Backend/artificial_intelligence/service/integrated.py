# file: Backend/artificial_intelligence/service/integrated.py

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage, HumanMessage

from Backend.artificial_intelligence.agent.agent_core import fallback_completion
from Backend.artificial_intelligence.agent.interface import process_chat_request
from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
)


def _parse_tool_media_parts(content: str) -> Optional[Dict[str, Any]]:
    """
    [重写] 从工具返回的完整 API 响应中提取所有媒体 part。

    Args:
        content: 工具返回的 JSON 字符串 (完整 Envelope)

    Returns:
        List[Dict]: 提取出的标准 part 列表
    """
    found_parts: List[Dict[str, Any]] = []

    try:
        clean_content = content.strip()
        # 简单的 markdown 清洗
        if clean_content.startswith("```"):
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            else:
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]

        data = json.loads(clean_content.strip())

        # 验证必须是字典且包含 llm_content
        if not isinstance(data, dict):
            return []

        llm_content = data.get("llm_content", [])
        if not isinstance(llm_content, list):
            return []

        # 遍历 llm_content 列表
        for item in llm_content:
            parts = item.get("part", [])  # 获取 part 列表
            if isinstance(parts, list):
                for p in parts:
                    if not isinstance(p, dict):
                        continue
                    found_parts.append(p)

    except (json.JSONDecodeError, TypeError):
        pass

    return found_parts


def _extract_text_parts(msg: AIMessage) -> List[Dict[str, Any]]:
    """从 AIMessage 提取纯文本部分"""
    parts: List[Dict[str, Any]] = []
    content_str = ""

    if isinstance(msg.content, str):
        content_str = msg.content
    elif isinstance(msg.content, list):
        texts = []
        for block in msg.content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        content_str = "\n".join(texts)

    if content_str:
        parts.append(
            {
                "content_type": "text",
                "content_text": content_str,
                "content_url": "",
                "parameter": {},
            }
        )
    return parts


def handle_integrated_entrance(payload: Any) -> str:
    """
    统一聊天接口
    执行逻辑：... -> Tool(Input/Gen) -> Assistant (Adsorption)
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})

    try:
        llm_content = request_data.get("llm_content", [])
        if not isinstance(llm_content, list) or not llm_content:
            raise ValueError("llm_content 不能为空")

        # 运行 Agent
        result = process_chat_request(request_data)
        messages: List[BaseMessage] = result["messages"]
        session_id = result["session_id"]
        pending_history = result["pending_history"]

        llm_content_list: List[Dict[str, Any]] = []

        # --- 核心逻辑：媒体吸附 ---
        # 暂存区：存放尚未被 Assistant 认领的工具媒体
        accumulated_tool_parts: List[Dict[str, Any]] = []
        has_assistant_response = False

        for msg in messages:
            if isinstance(msg, HumanMessage):
                # 遇到 Human，打断了吸附链，清空暂存区 (防止上文的图片挂到下文的回答)
                accumulated_tool_parts = []

            elif isinstance(msg, ToolMessage):
                # 解析并暂存工具媒体
                media_parts = _parse_tool_media_parts(msg.content)
                if media_parts:
                    accumulated_tool_parts += media_parts

            elif isinstance(msg, AIMessage):
                text_parts = _extract_text_parts(msg)

                current_parts = text_parts + accumulated_tool_parts

                # 只有当有实质内容时才添加
                if current_parts:
                    llm_content_list.append(
                        {
                            "role": "assistant",
                            "interface_type": "integrated",
                            "sent_time_stamp": int(time.time()),
                            "part": current_parts,
                        }
                    )
                    has_assistant_response = True

                # 完成吸附，清空暂存区
                accumulated_tool_parts = []

        # --- Fallback 处理 ---
        if not has_assistant_response:
            fallback_text = fallback_completion(pending_history)
            if not fallback_text:
                raise ValueError("Agent 未返回有效响应")

            # 将残留的工具媒体和 Fallback 文本一并输出
            parts = accumulated_tool_parts + [
                {
                    "content_type": "text",
                    "content_text": fallback_text,
                    "content_url": "",
                    "parameter": {},
                }
            ]

            llm_content_list.append(
                {
                    "role": "assistant",
                    "interface_type": "integrated",
                    "sent_time_stamp": int(time.time()),
                    "part": parts,
                }
            )

        return build_success_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            llm_content=llm_content_list,
        )

    except Exception as exc:
        session_id = request_data.get("session_id", "default")
        return build_error_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_integrated_entrance"]
