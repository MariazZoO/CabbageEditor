from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from Backend.artificial_intelligence.agent.agent_core import fallback_completion
from Backend.artificial_intelligence.agent.interface import process_chat_request

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
)


def handle_integrated_entrance(payload: Any) -> str:
    """统一聊天接口三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})
    try:
        # 提前验证输入
        llm_content = request_data.get("llm_content", [])
        if not isinstance(llm_content, list) or not llm_content:
            raise ValueError("llm_content 不能为空")

        result = process_chat_request(request_data)
        messages = result["messages"]
        session_id = result["session_id"]
        pending_history = result["pending_history"]

        llm_content_list: List[Dict[str, Any]] = []
        has_valid_content = False

        for msg in messages:
            parts: List[Dict[str, Any]] = []
            role = "assistant"

            if isinstance(msg, HumanMessage):
                role = "user"
                if isinstance(msg.content, str):
                    parts.append({"content_type": "text", "content_text": msg.content})
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                parts.append(
                                    {
                                        "content_type": "text",
                                        "content_text": block.get("text"),
                                    }
                                )
                            elif block.get("type") == "image_url":
                                url = block.get("image_url", {}).get("url")
                                if url:
                                    parts.append(
                                        {"content_type": "image", "content_url": url}
                                    )

            elif isinstance(msg, AIMessage):
                role = "assistant"
                if msg.content:
                    if isinstance(msg.content, str):
                        parts.append(
                            {"content_type": "text", "content_text": msg.content}
                        )
                    elif isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    parts.append(
                                        {
                                            "content_type": "text",
                                            "content_text": block.get("text"),
                                        }
                                    )

            elif isinstance(msg, ToolMessage):
                try:
                    envelope = json.loads(str(msg.content))
                    if isinstance(envelope, dict) and "llm_content" in envelope:
                        for item in envelope["llm_content"]:
                            # 清洗 parameter
                            if "part" in item and isinstance(item["part"], list):
                                cleaned_parts = []
                                for part in item["part"]:
                                    cleaned_part = {
                                        "content_type": part.get("content_type"),
                                        "content_url": part.get("content_url"),
                                        "content_text": part.get("content_text"),
                                    }
                                    if "parameter" in part:
                                        original_param = part["parameter"]
                                        cleaned_param = {}
                                        # 白名单过滤
                                        allowed_params = [
                                            "resolution",
                                            "duration",
                                            "speech_type",
                                            "music_style",
                                            "text_type",
                                        ]
                                        for key in allowed_params:
                                            if key in original_param:
                                                cleaned_param[key] = original_param[key]
                                        if cleaned_param:
                                            cleaned_part["parameter"] = cleaned_param

                                    cleaned_part = {
                                        k: v
                                        for k, v in cleaned_part.items()
                                        if v is not None
                                    }
                                    cleaned_parts.append(cleaned_part)
                                item["part"] = cleaned_parts

                            llm_content_list.append(item)
                            has_valid_content = True
                        continue
                    else:
                        parts.append(
                            {"content_type": "text", "content_text": str(msg.content)}
                        )
                        role = "tool"
                except Exception:
                    parts.append(
                        {"content_type": "text", "content_text": str(msg.content)}
                    )
                    role = "tool"

            if parts:
                llm_content_list.append(
                    {
                        "role": role,
                        "interface_type": "integrated",
                        "sent_time_stamp": int(time.time()),
                        "part": parts,
                    }
                )
                has_valid_content = True

        has_assistant_or_tool = any(
            item["role"] in ("assistant", "tool", "tools") for item in llm_content_list
        )

        if not has_assistant_or_tool:
            content = fallback_completion(pending_history)
            if content:
                llm_content_list.append(
                    {
                        "role": "assistant",
                        "interface_type": "integrated",
                        "sent_time_stamp": int(time.time()),
                        "part": [{"content_type": "text", "content_text": content}],
                    }
                )
                has_valid_content = True

        if not has_valid_content:
            raise ValueError("请求中既没有文本内容也没有图片")

        return build_success_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            llm_content=llm_content_list,
        )
    except Exception as exc:  # noqa: BLE001
        session_id = request_data.get("session_id", "default")
        return build_error_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_integrated_entrance"]
