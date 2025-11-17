from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from Backend.artificial_intelligence.agent.executor import run_agent
from Backend.artificial_intelligence.agent.conversation import (
    default_session_id,
    get_history,
    update_history,
)
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from Backend.artificial_intelligence.agent.adapters import (
    build_user_message,
    coerce_messages,
    extract_image_payload,
    extract_text,
    log_ai_messages,
)
from Backend.artificial_intelligence.config.config import get_app_config
from Backend.artificial_intelligence.models import get_chat_model
from Backend.artificial_intelligence.tools.storage import get_image_store
from Backend.artificial_intelligence.tools.session import (
    reset_current_session,
    set_current_session,
)
from Backend.utils.bootstrap import bootstrap

from Backend.artificial_intelligence.agent.requests import (
    normalize_request,
    normalize_upload_request,
)
from Backend.artificial_intelligence.tools.image_handler import register_uploads

bootstrap()
_IMAGE_STORE = get_image_store()


def invoke_messages(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    直接使用 LangChain 标准的 BaseMessage 列表调用 agent。
    """
    result = run_agent(messages)
    log_ai_messages(result)
    return result


def handle_image_upload(payload: Any) -> str:
    request = normalize_upload_request(payload, default_session_id())
    stored = _IMAGE_STORE.save_upload(
        session_id=request.session_id,
        data=request.data,
        category=request.category,
        original_name=request.name,
    )
    url = _IMAGE_STORE.build_url(stored)
    response = {
        "type": "image_upload",
        "status": "success",
        "timestamp": int(time.time()),
        "session_id": request.session_id,
        "token": request.token,
        "image": {
            "name": stored.name,
            "url": url,
            "category": request.category,
        },
    }
    return json.dumps(response, ensure_ascii=False)


def handle_user_message(message: Any) -> str:
    request = normalize_request(message, default_session_id())
    stored_history = get_history(request.session_id)

    upload_notes = register_uploads(request)
    user_message = build_user_message(request, upload_notes)
    # user_message为dict，需转为BaseMessage
    pending_history = [*stored_history, HumanMessage(content=user_message["content"])]

    token = set_current_session(request.session_id)
    try:
        # 直接传递 BaseMessage 列表给 agent，不需要转化为 dict
        state = invoke_messages(pending_history)
    finally:
        reset_current_session(token)

    messages = coerce_messages(state)
    # messages为dict列表，提取assistant消息并转为AIMessage
    history_extension = []
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = m.get("content")
            # 确保content为数组
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            history_extension.append(AIMessage(content=content))
        elif isinstance(m, AIMessage):
            history_extension.append(m)
    update_history(request.session_id, [*pending_history, *history_extension])

    content = extract_text(messages)
    if not content.strip():
        content = _fallback_completion(pending_history)

    image_payload = extract_image_payload(messages)
    payload: Dict[str, Any] = {
        "type": (
            image_payload.get("type", "ai_response") if image_payload else "ai_response"
        ),
        "content": content,
        "status": "success",
        "timestamp": int(time.time()),
        "session_id": request.session_id,
    }
    if image_payload:
        payload.update(
            {
                "image_base64": image_payload.get("image_base64"),
                "image_name": image_payload.get("image_name"),
                "image_path": image_payload.get("image_path"),
                "image_url": image_payload.get("image_url"),
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def _fallback_completion(history: List[BaseMessage]) -> str:
    """
    备用完成方法：直接使用 LLM 而不经过 agent。
    接受标准的 LangChain BaseMessage 列表。
    """
    cfg = get_app_config()
    chat_cfg = cfg.chat
    llm = get_chat_model(
        cfg,
        provider_name=chat_cfg.provider,
        model_name=chat_cfg.model,
        temperature=chat_cfg.temperature,
        request_timeout=chat_cfg.request_timeout,
    )
    # 添加系统提示
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=chat_cfg.system_prompt),
        *history,
    ]
    ai_message = llm.invoke(prompt_messages)
    content = ai_message.content or ""
    # content为数组时提取text
    if isinstance(content, list):
        content = "\n".join([b["text"] for b in content if b.get("type") == "text"])
    print(f"[AIMessage] {content}")
    return content


__all__ = ["invoke_messages", "handle_user_message", "handle_image_upload"]
