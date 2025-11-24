# file: Backend/artificial_intelligence/service/integrated.py

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, ToolMessage, BaseMessage, HumanMessage

from Backend.artificial_intelligence.agent.executor import fallback_completion
from Backend.artificial_intelligence.agent.interface import process_chat_request
from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
)


def _parse_tool_parts(content: str) -> List[Dict[str, Any]]:
    """
    [修改] 解析工具返回的完整 API 响应 Envelope。
    现在支持提取所有类型的 part (包括 text)，不仅仅是媒体。
    """
    found_parts = []
    try:
        # 1. 清洗 content
        clean_content = content.strip()
        if clean_content.startswith("```"):
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            else:
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]

        # 2. 解析 JSON
        data = json.loads(clean_content.strip())

        # 3. 钻取: llm_content -> list -> part -> list
        if isinstance(data, dict):
            llm_content = data.get("llm_content", [])
            if isinstance(llm_content, list):
                for item in llm_content:
                    parts = item.get("part", [])
                    if isinstance(parts, list):
                        for p in parts:
                            if isinstance(p, dict):
                                c_type = p.get("content_type")
                                # [关键修改] 放开类型限制，允许 text 通过，以便后续逻辑判断
                                if c_type in ["image", "audio", "video", "text"]:
                                    found_parts.append(p)
    except Exception:
        # 解析失败忽略，视为无有效 part
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
    执行逻辑：Assistant (Thought) -> Tool (Result) [挂载到前者]
    特殊情况：Tool (Text) -> 独立消息
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

        # --- 1. 确定处理范围 ---
        # 找到最后一条 HumanMessage 的位置，只处理它之后产生的消息 (即本次 Agent 的思考和行动)
        start_index = 0
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                start_index = i + 1
                break

        relevant_messages = messages[start_index:]

        # --- 2. 核心处理逻辑 ---
        # last_assistant_entry 指向 llm_content_list 中最近的一个 assistant 消息对象（字典）
        # 用于将后续的 Tool 媒体 part 挂载进去
        last_assistant_entry: Optional[Dict[str, Any]] = None

        for msg in relevant_messages:

            # === 处理 AI 消息 ===
            if isinstance(msg, AIMessage):
                text_parts = _extract_text_parts(msg)
                if text_parts:
                    # 创建新的 Assistant 消息
                    new_entry = {
                        "role": "assistant",
                        "interface_type": "integrated",
                        "sent_time_stamp": int(time.time()),
                        "part": text_parts,
                    }
                    llm_content_list.append(new_entry)
                    # 更新指针，后续的 Tool 媒体将挂载到这里
                    last_assistant_entry = new_entry

            # === 处理 Tool 消息 ===
            elif isinstance(msg, ToolMessage):
                tool_parts = _parse_tool_parts(msg.content)
                for part in tool_parts:
                    c_type = part.get("content_type")

                    # 情况 A: 媒体资源 (Image/Audio/Video)
                    # 需求：挂载到前一个 Assistant 上
                    if c_type in ["image", "audio", "video"]:
                        if last_assistant_entry is not None:
                            last_assistant_entry["part"].append(part)
                        else:
                            # 边界情况：Tool 之前没有 Assistant (罕见)，创建独立消息
                            new_entry = {
                                "role": "assistant",
                                "interface_type": "integrated",
                                "sent_time_stamp": int(time.time()),
                                "part": [part],
                            }
                            llm_content_list.append(new_entry)
                            last_assistant_entry = new_entry

                    # 情况 B: 纯文本内容
                    # 需求：构造一个独立的 Assistant 消息
                    elif c_type == "text":
                        new_entry = {
                            "role": "assistant",
                            "interface_type": "integrated",
                            "sent_time_stamp": int(time.time()),
                            "part": [part],
                        }
                        llm_content_list.append(new_entry)
                        # 更新指针，如果这个文本工具后面紧跟了图片，图片会挂在这个文本消息下(通常合理)
                        # 或者你可以选择不更新指针，让图片继续挂在 Agent 的 Thought 上，取决于业务定义
                        # 这里选择更新指针，视作最新的上下文节点
                        last_assistant_entry = new_entry

        # --- Fallback 处理 ---
        # 如果跑完一圈没有任何输出 (例如 Agent 直接崩了没说话)，使用 Fallback
        if not llm_content_list:
            fallback_text = fallback_completion(pending_history)
            if not fallback_text:
                raise ValueError("Agent 未返回有效响应")

            llm_content_list.append(
                {
                    "role": "assistant",
                    "interface_type": "integrated",
                    "sent_time_stamp": int(time.time()),
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": fallback_text,
                            "content_url": "",
                            "parameter": {},
                        }
                    ],
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
