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
from Backend.artificial_intelligence.storage import get_media_store
from Backend.artificial_intelligence.tools.session import (
    reset_current_session,
    set_current_session,
)
from Backend.artificial_intelligence.agent.requests import (
    normalize_request,
    normalize_upload_request,
)

from Backend.artificial_intelligence.models.client_image import LingyaImageClient
from Backend.artificial_intelligence.models.client_video import DashScopeVideoClient

_MEDIA_STORE = get_media_store()


def handle_image_generation(payload: Any) -> str:
    """
    处理独立的图像生成请求

    请求格式:
    {
        "prompt": "生成图像的提示词",
        "session_id": "session_xxx",
        "product_url": "autosave://...",  // 可选
        "scene_url": "autosave://...",    // 可选
        "use_references": false           // 可选
    }
    """
    try:
        request_data = payload if isinstance(payload, dict) else {}
        prompt = request_data.get("prompt")
        if not prompt:
            raise ValueError("缺少必需参数: prompt")

        session_id = request_data.get("session_id", default_session_id())
        product_url = request_data.get("product_url")
        scene_url = request_data.get("scene_url")
        use_references = request_data.get("use_references", False)

        # 获取配置
        cfg = get_app_config()
        image_cfg = cfg.media.image

        if not image_cfg.enable:
            raise RuntimeError("图像生成功能未启用")

        if not image_cfg.provider or not image_cfg.model:
            raise RuntimeError("图像生成配置不完整")

        if image_cfg.provider not in cfg.providers:
            raise RuntimeError(f"未找到提供商配置: {image_cfg.provider}")

        provider = cfg.providers[image_cfg.provider]
        if not provider.api_key or not provider.base_url:
            raise RuntimeError(f"提供商 '{image_cfg.provider}' 配置不完整")

        # 创建客户端
        client = LingyaImageClient(
            provider=provider,
            model=image_cfg.model,
            base_url=image_cfg.base_url,
        )

        # 自动引用会话中的图片
        if use_references:
            from Backend.artificial_intelligence.tools.media.image_tools import (
                _latest_upload_url,
            )

            product_url = product_url or _latest_upload_url(
                _MEDIA_STORE, session_id, "product"
            )
            scene_url = scene_url or _latest_upload_url(
                _MEDIA_STORE, session_id, "scene"
            )

        # 生成图像
        image_b64, mime_type = client.generate(
            prompt=prompt,
            store=_MEDIA_STORE,
            product_url=product_url,
            scene_url=scene_url,
        )

        # 保存生成的图像
        stored = _MEDIA_STORE.save_generated_image(
            session_id=session_id,
            data_base64=f"data:{mime_type};base64,{image_b64}",
            mime_type=mime_type,
        )

        image_url = _MEDIA_STORE.build_image_url(stored)

        # 构建响应
        response = {
            "type": "image_generation",
            "status": "success",
            "timestamp": int(time.time()),
            "session_id": session_id,
            "prompt": prompt,
            "image": {
                "name": stored.name,
                "path": str(stored.path),
                "url": image_url,
                "base64": image_b64,
            },
        }

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "image_generation",
            "status": "error",
            "timestamp": int(time.time()),
            "session_id": request_data.get("session_id", default_session_id()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


def handle_video_generation(payload: Any) -> str:
    """
    处理独立的视频生成请求（图生视频）

    请求格式:
    {
        "prompt": "视频生成提示词",
        "image_url": "autosave://...",     // 输入图片URL（支持 autosave://、file://、http(s)://、data URI、本地路径）
        "session_id": "session_xxx",       // 可选
        "resolution": "720P",              // 可选：480P/720P/1080P
        "prompt_extend": true,             // 可选：是否扩展提示词
        "download_video": true             // 可选：是否下载视频到本地
    }
    """
    try:
        request_data = payload if isinstance(payload, dict) else {}
        prompt = request_data.get("prompt")
        image_url = request_data.get("image_url")

        if not prompt:
            raise ValueError("缺少必需参数: prompt")
        if not image_url:
            raise ValueError("缺少必需参数: image_url")

        session_id = request_data.get("session_id", default_session_id())
        resolution = request_data.get("resolution", "720P")
        prompt_extend = request_data.get("prompt_extend", True)
        download_video = request_data.get("download_video", True)

        # 获取配置
        cfg = get_app_config()
        video_cfg = cfg.media.video

        if not video_cfg.enable:
            raise RuntimeError("视频生成功能未启用")

        if not video_cfg.provider or not video_cfg.model:
            raise RuntimeError("视频生成配置不完整")

        if video_cfg.provider not in cfg.providers:
            raise RuntimeError(f"未找到提供商配置: {video_cfg.provider}")

        provider = cfg.providers[video_cfg.provider]
        if not provider.api_key:
            raise RuntimeError(f"提供商 '{video_cfg.provider}' 缺少 API Key")

        # 创建客户端
        client = DashScopeVideoClient(
            provider=provider,
            model=video_cfg.model,
            base_url=video_cfg.base_url,
        )

        # 解析图片 URL（使用统一的工具函数）
        from Backend.artificial_intelligence.models.video_utils import resolve_image_url

        resolved_url = resolve_image_url(image_url, _MEDIA_STORE)
        if not resolved_url:
            raise ValueError(f"无法加载图片：{image_url}")

        # 生成视频
        result = client.generate_video_from_image(
            prompt=prompt,
            image_url=resolved_url,
            resolution=resolution,
            prompt_extend=prompt_extend,
            max_wait_seconds=600,
            poll_interval=5.0,
        )

        # 构建响应
        response = {
            "type": "video_generation",
            "status": "success",
            "timestamp": int(time.time()),
            "session_id": session_id,
            "prompt": prompt,
            "source": provider.name,
            "model": client.model,
            "video_url": result.get("output", {}).get("video_url"),
            "task_id": result.get("task_id"),
            "resolution": resolution,
        }

        # 添加可选字段
        output = result.get("output", {})
        if "orig_prompt" in output:
            response["orig_prompt"] = output["orig_prompt"]
        if "actual_prompt" in output:
            response["actual_prompt"] = output["actual_prompt"]
        if "usage" in result:
            response["usage"] = result["usage"]

        # 如果需要，下载视频到本地
        if download_video and response["video_url"]:
            try:
                stored_video = _MEDIA_STORE.download_and_save_video(
                    session_id=session_id,
                    video_url=response["video_url"],
                    task_id=response["task_id"],
                    prompt=prompt,
                    source_image_url=image_url,
                )

                # 添加本地存储信息
                response["local_video"] = {
                    "name": stored_video.name,
                    "path": str(stored_video.path),
                    "url": _MEDIA_STORE.build_video_url(stored_video),
                    "file_size_mb": stored_video.file_size_mb,
                }
            except Exception as e:
                # 下载失败不影响主流程
                response["download_error"] = str(e)

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "video_generation",
            "status": "error",
            "timestamp": int(time.time()),
            "session_id": request_data.get("session_id", default_session_id()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


def invoke_messages(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    直接使用 LangChain 标准的 BaseMessage 列表调用 agent。
    """
    result = run_agent(messages)
    log_ai_messages(result)
    return result


def handle_image_upload(payload: Any) -> str:
    request = normalize_upload_request(payload, default_session_id())
    stored = _MEDIA_STORE.save_upload(
        session_id=request.session_id,
        data=request.data,
        category=request.category,
        original_name=request.name,
    )
    url = _MEDIA_STORE.build_image_url(stored)
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

    upload_notes = _MEDIA_STORE.register_uploads(request)
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


__all__ = [
    "invoke_messages",
    "handle_user_message",
    "handle_image_upload",
    "handle_image_generation",
    "handle_video_generation",
]
