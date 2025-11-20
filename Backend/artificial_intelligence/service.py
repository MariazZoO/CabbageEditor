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
from Backend.artificial_intelligence.config.ai_config import get_ai_config
from Backend.artificial_intelligence.models import get_chat_model
from Backend.artificial_intelligence.storage import get_media_store
from Backend.artificial_intelligence.tools.session import (
    reset_current_session,
    set_current_session,
)

from Backend.artificial_intelligence.agent.requests import normalize_request


_MEDIA_STORE = get_media_store()


def handle_integrated_entrance(payload: Any) -> str:
    """
    统一的聊天接口，支持以下三种调用方式：

    1. 用户消息（带图片上传）:
    {
        "message": "用户输入的文本",
        "session_id": "session_xxx",      // 可选
        "images": [                        // 可选，图片附件数组
            {
                "name": "image1.jpg",
                "type": "product",         // product/scene
                "data": "base64...",       // base64编码或data URI
                "url": "http://..."        // 或者使用URL
            }
        ]
    }

    2. 简单文本消息:
    "用户的文本消息"

    3. LangChain标准消息列表:
    [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ]
    或直接传递 List[BaseMessage]
    """
    try:
        # 情况3: 检查是否是 LangChain 消息列表
        if isinstance(payload, list):
            # 检查是否是 BaseMessage 列表
            if payload and isinstance(payload[0], BaseMessage):
                return _build_langchain_messages(payload, default_session_id())
            # 检查是否是标准消息格式的字典列表
            elif payload and isinstance(payload[0], dict) and "role" in payload[0]:
                # 转换为 BaseMessage 列表
                messages = _convert_to_base_messages(payload)
                return _build_langchain_messages(messages, default_session_id())

        # 情况1和2: 用户消息（可能带图片）
        request = normalize_request(payload, default_session_id())
        stored_history = get_history(request.session_id)

        user_message = build_user_message(request)
        # user_message为dict，需转为BaseMessage
        pending_history = [
            *stored_history,
            HumanMessage(content=user_message["content"]),
        ]

        token = set_current_session(request.session_id)
        try:
            # 直接调用 agent
            state = run_agent(pending_history)
            log_ai_messages(state)
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
        response: Dict[str, Any] = {
            "type": (
                image_payload.get("type", "ai_response")
                if image_payload
                else "ai_response"
            ),
            "content": content,
            "status": "success",
            "timestamp": int(time.time()),
            "session_id": request.session_id,
        }
        if image_payload:
            response.update(
                {
                    "image_base64": image_payload.get("image_base64"),
                    "image_name": image_payload.get("image_name"),
                    "image_path": image_payload.get("image_path"),
                    "image_url": image_payload.get("image_url"),
                }
            )
        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "ai_response",
            "status": "error",
            "timestamp": int(time.time()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


def handle_image_generation(payload: Any) -> str:
    """
    处理独立的图像生成请求

    请求格式:
    {
        "prompt": "生成图像的提示词",
        "session_id": "session_xxx",      // 可选，用于会话管理
        "product_url": "data:image/...",  // 可选，base64或URL
        "scene_url": "data:image/..."     // 可选，base64或URL
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

        # 获取配置并加载工具
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.image_tools import (
            load_image_tools,
        )

        tools = load_image_tools(cfg)
        if not tools:
            raise RuntimeError("图像生成功能未启用或配置不完整")

        image_tool = tools[0]

        # 调用工具生成图像（只传递工具需要的参数）
        token = set_current_session(session_id)
        try:
            result_json = image_tool.func(
                prompt=prompt,
                product_url=product_url,
                scene_url=scene_url,
            )
        finally:
            reset_current_session(token)

        # 解析工具返回的结果
        tool_result = json.loads(result_json)

        # 工具返回的是图片URL（HTTP URL或data URI）
        image_url = tool_result.get("image_url", "")

        # 构建响应（保持与原接口一致）
        response = {
            "type": "image_generation",
            "status": "success",
            "timestamp": int(time.time()),
            "session_id": session_id,
            "prompt": tool_result.get("prompt", prompt),
            "image": {
                "name": "",
                "path": "",
                "url": image_url,
                "base64": "",  # 不再返回base64，前端需要时可以从URL加载
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
        "image_url": "data:image/...",    // 输入图片URL（支持 file://、http(s)://、data URI、本地路径）
        "session_id": "session_xxx",      // 可选，用于会话管理
        "resolution": "720P",             // 可选：480P/720P/1080P
        "prompt_extend": true              // 可选：是否扩展提示词
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

        # 获取配置并加载工具
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.video_tools import (
            load_video_tools,
        )

        tools = load_video_tools(cfg)
        if not tools:
            raise RuntimeError("视频生成功能未启用或配置不完整")

        video_tool = tools[0]

        # 调用工具生成视频（只传递工具需要的参数）
        token = set_current_session(session_id)
        try:
            result_json = video_tool.func(
                prompt=prompt,
                image_url=image_url,
                resolution=resolution,
                prompt_extend=prompt_extend,
            )
        finally:
            reset_current_session(token)

        # 解析工具返回的结果
        tool_result = json.loads(result_json)

        # 构建响应（保持与原接口一致）
        response = {
            "type": "video_generation",
            "status": (
                "success"
                if tool_result.get("status") == "succeeded"
                else tool_result.get("status", "success")
            ),
            "timestamp": int(time.time()),
            "session_id": session_id,
            "prompt": tool_result.get("prompt", prompt),
            "source": tool_result.get("source", ""),
            "model": tool_result.get("model", ""),
            "video_url": tool_result.get("video_url", ""),
            "task_id": tool_result.get("task_id", ""),
            "resolution": tool_result.get("resolution", resolution),
        }

        # 添加可选字段
        if "orig_prompt" in tool_result:
            response["orig_prompt"] = tool_result["orig_prompt"]
        if "actual_prompt" in tool_result:
            response["actual_prompt"] = tool_result["actual_prompt"]
        if "usage" in tool_result:
            response["usage"] = tool_result["usage"]
        if "local_video" in tool_result:
            response["local_video"] = tool_result["local_video"]
        if "download_error" in tool_result:
            response["download_error"] = tool_result["download_error"]

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


def _convert_to_base_messages(message_dicts: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    将标准消息格式转换为 LangChain BaseMessage 列表
    """
    messages: List[BaseMessage] = []
    for msg in message_dicts:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            messages.append(SystemMessage(content=content))
        elif role in ("user", "human"):
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))
        else:
            # 默认作为用户消息处理
            messages.append(HumanMessage(content=content))

    return messages


def _build_langchain_messages(messages: List[BaseMessage], session_id: str) -> str:
    """
    处理 LangChain 消息列表的内部方法
    """
    token = set_current_session(session_id)
    try:
        state = run_agent(messages)
        log_ai_messages(state)
    finally:
        reset_current_session(token)

    response_messages = coerce_messages(state)
    content = extract_text(response_messages)

    if not content.strip():
        content = _fallback_completion(messages)

    image_payload = extract_image_payload(response_messages)
    response: Dict[str, Any] = {
        "type": (
            image_payload.get("type", "ai_response") if image_payload else "ai_response"
        ),
        "content": content,
        "status": "success",
        "timestamp": int(time.time()),
        "session_id": session_id,
    }
    if image_payload:
        response.update(
            {
                "image_base64": image_payload.get("image_base64"),
                "image_name": image_payload.get("image_name"),
                "image_path": image_payload.get("image_path"),
                "image_url": image_payload.get("image_url"),
            }
        )
    return json.dumps(response, ensure_ascii=False)


def _fallback_completion(history: List[BaseMessage]) -> str:
    """
    备用完成方法：直接使用 LLM 而不经过 agent。
    接受标准的 LangChain BaseMessage 列表。
    """
    cfg = get_ai_config()
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


def handle_text_generation(payload: Any) -> str:
    """
    处理独立的文案生成请求

    请求格式:
    {
        "type": "product|marketing|creative",  // 文案类型
        "session_id": "session_xxx",           // 可选，用于会话管理

        // 产品文案参数
        "product_name": "产品名称",
        "product_features": "特点1,特点2",
        "style": "专业",                       // 可选：专业、活泼、高端、亲切、幽默
        "length": "中等",                      // 可选：简短、中等、详细

        // 营销文案参数
        "theme": "营销主题",
        "target_audience": "目标受众",
        "key_points": "要点1,要点2",
        "platform": "通用",                    // 可选：通用、微信、微博、抖音、小红书
        "tone": "激励",                        // 可选：激励、温暖、紧迫、趣味

        // 创意文案参数
        "content_type": "故事|诗歌|剧本等",
        "theme": "创作主题",
        "keywords": "关键词1,关键词2",         // 可选
        "style": "现代"                        // 可选：现代、古典、浪漫、科技、悬疑等
    }
    """
    try:
        request_data = payload if isinstance(payload, dict) else {}
        copywriting_type = request_data.get("type", "product")

        if copywriting_type not in ["product", "marketing", "creative"]:
            raise ValueError(f"不支持的文案类型: {copywriting_type}")

        session_id = request_data.get("session_id", default_session_id())

        # 获取配置并加载工具
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.copywriting import (
            load_copywriting_tools,
        )

        tools = load_copywriting_tools(cfg)
        if not tools:
            raise RuntimeError("文案生成功能未启用或配置不完整")

        # 根据类型选择对应的工具
        tool_map = {
            "product": "generate_product_copywriting",
            "marketing": "generate_marketing_copywriting",
            "creative": "generate_creative_copywriting",
        }

        tool_name = tool_map[copywriting_type]
        copywriting_tool = None
        for tool in tools:
            if tool.name == tool_name:
                copywriting_tool = tool
                break

        if not copywriting_tool:
            raise RuntimeError(f"未找到文案生成工具: {tool_name}")

        # 准备工具调用参数
        tool_params = {}
        if copywriting_type == "product":
            tool_params = {
                "product_name": request_data.get("product_name", ""),
                "product_features": request_data.get("product_features", ""),
                "style": request_data.get("style", "专业"),
                "length": request_data.get("length", "中等"),
            }
        elif copywriting_type == "marketing":
            tool_params = {
                "theme": request_data.get("theme", ""),
                "target_audience": request_data.get("target_audience", ""),
                "key_points": request_data.get("key_points", ""),
                "platform": request_data.get("platform", "通用"),
                "tone": request_data.get("tone", "激励"),
            }
        elif copywriting_type == "creative":
            tool_params = {
                "content_type": request_data.get("content_type", ""),
                "theme": request_data.get("theme", ""),
                "keywords": request_data.get("keywords"),
                "style": request_data.get("style", "现代"),
                "length": request_data.get("length", "中等"),
            }

        # 调用工具生成文案
        token = set_current_session(session_id)
        try:
            result = copywriting_tool.func(**tool_params)
        finally:
            reset_current_session(token)

        # 构建响应
        response = {
            "type": "copywriting_generation",
            "copywriting_type": copywriting_type,
            "status": "success",
            "timestamp": int(time.time()),
            "session_id": session_id,
            "content": result,
        }

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "copywriting_generation",
            "status": "error",
            "timestamp": int(time.time()),
            "session_id": request_data.get("session_id", default_session_id()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


def handle_speech_generation(payload: Any) -> str:
    """
    处理独立的TTS语音合成请求

    请求格式:
    {
        "text": "待合成的文本内容",
        "session_id": "session_xxx",           // 可选，用于会话管理
        "voice_type": "zh_female_cancan_mars_bigtts",  // 可选，音色类型
        "speed_ratio": 1.0,                    // 可选，语速比例 [0.5, 2.0]
        "loudness_ratio": 1.0,                 // 可选，音量比例 [0.5, 2.0]
        "encoding": "mp3",                     // 可选，音频格式
        "rate": 24000,                         // 可选，采样率
        "max_wait_seconds": 60,                // 可选，最大等待时间
        "poll_interval": 2.0                   // 可选，轮询间隔
    }
    """
    try:
        request_data = payload if isinstance(payload, dict) else {}
        text = request_data.get("text")

        if not text:
            raise ValueError("缺少必需参数: text")

        session_id = request_data.get("session_id", default_session_id())

        # 获取配置并加载工具
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.tts_tools import (
            load_tts_tools,
        )

        tools = load_tts_tools(cfg)
        if not tools:
            raise RuntimeError("TTS语音合成功能未启用或配置不完整")

        tts_tool = tools[0]

        # 准备工具调用参数
        tool_params = {
            "text": text,
            "voice_type": request_data.get(
                "voice_type", "zh_female_cancan_mars_bigtts"
            ),
            "speed_ratio": request_data.get("speed_ratio", 1.0),
            "loudness_ratio": request_data.get("loudness_ratio", 1.0),
            "encoding": request_data.get("encoding", "mp3"),
            "rate": request_data.get("rate", 24000),
            "max_wait_seconds": request_data.get("max_wait_seconds", 60),
            "poll_interval": request_data.get("poll_interval", 2.0),
        }

        # 调用工具生成语音
        token = set_current_session(session_id)
        try:
            result_json = tts_tool.func(**tool_params)
        finally:
            reset_current_session(token)

        # 解析工具返回的结果
        tool_result = json.loads(result_json)

        # 构建响应
        response = {
            "type": "tts_generation",
            "status": tool_result.get("status", "success"),
            "timestamp": int(time.time()),
            "session_id": session_id,
            "task_id": tool_result.get("task_id"),
            "audio_url": tool_result.get("audio_url"),
            "duration": tool_result.get("duration"),
            "req_text_length": tool_result.get("req_text_length"),
            "url_expire_time": tool_result.get("url_expire_time"),
            "encoding": tool_result.get("encoding"),
            "voice_type": tool_result.get("voice_type"),
            "error": tool_result.get("error"),
        }

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "tts_generation",
            "status": "error",
            "timestamp": int(time.time()),
            "session_id": request_data.get("session_id", default_session_id()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


def handle_music_generation(payload: Any) -> str:
    """
    处理独立的BGM音乐生成请求

    请求格式:
    {
        "prompt": "音乐描述提示词",
        "session_id": "session_xxx",           // 可选，用于会话管理
        "style": "lofi",                       // 可选，音乐风格
        "model": "V5",                         // 可选，模型版本
        "duration": 20,                        // 可选，音乐时长（秒）
        "wait": false,                         // 可选，是否等待生成完成
        "max_wait_seconds": 600,               // 可选，最大等待时间
        "poll_interval": 5.0                   // 可选，轮询间隔
    }
    """
    try:
        request_data = payload if isinstance(payload, dict) else {}
        prompt = request_data.get("prompt")

        if not prompt:
            raise ValueError("缺少必需参数: prompt")

        session_id = request_data.get("session_id", default_session_id())

        # 获取配置并加载工具
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.music_tools import (
            load_music_tools,
        )

        tools = load_music_tools(cfg)
        if not tools:
            raise RuntimeError("BGM音乐生成功能未启用或配置不完整")

        music_tool = tools[0]

        # 准备工具调用参数
        tool_params = {
            "prompt": prompt,
            "style": request_data.get("style", ""),
            "model": request_data.get("model", "V5"),
            "duration": request_data.get("duration", 20),
            "wait": request_data.get("wait", False),
            "max_wait_seconds": request_data.get("max_wait_seconds", 600),
            "poll_interval": request_data.get("poll_interval", 5.0),
        }

        # 调用工具生成音乐
        token = set_current_session(session_id)
        try:
            result_json = music_tool.func(**tool_params)
        finally:
            reset_current_session(token)

        # 解析工具返回的结果
        tool_result = json.loads(result_json)

        # 构建响应
        response = {
            "type": "music_generation",
            "status": tool_result.get("status", "success"),
            "timestamp": int(time.time()),
            "session_id": session_id,
            "task_id": tool_result.get("task_id"),
            "model": tool_result.get("model"),
            "prompt": tool_result.get("prompt"),
            "style": tool_result.get("style"),
            "audio_list": tool_result.get("audio_list", []),
            "audio_count": tool_result.get("audio_count", 0),
            "error": tool_result.get("error"),
        }

        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        error_response = {
            "type": "music_generation",
            "status": "error",
            "timestamp": int(time.time()),
            "session_id": request_data.get("session_id", default_session_id()),
            "content": str(e),
        }
        return json.dumps(error_response, ensure_ascii=False)


__all__ = [
    "handle_integrated_entrance",
    "handle_image_generation",
    "handle_video_generation",
    "handle_text_generation",
    "handle_speech_generation",
    "handle_music_generation",
]
