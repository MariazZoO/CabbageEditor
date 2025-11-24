import os
import sys
import uuid
import logging
import random
from datetime import datetime
from typing import Any, Dict

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

# 确保可以导入项目内模块（将项目根目录加入 sys.path）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 尝试导入现有 AI 服务函数（如果失败，仍可使用本文件的 stub 接口）
AI_AVAILABLE = True
try:
    from Backend.artificial_intelligence.service import (
        handle_integrated_entrance,
        handle_image_generation,
        handle_video_generation,
        handle_text_generation,
        handle_speech_generation,
        handle_music_generation,
    )
except Exception as e:  # noqa: BLE001
    AI_AVAILABLE = False
    logging.warning("AI service not available: %s", e)

# Flask 应用与 CORS 配置
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

# 静态文件（用于本文件的图片生成 stub）
STATIC_IMAGE_DIR = os.path.join(PROJECT_ROOT, "static", "images")
os.makedirs(STATIC_IMAGE_DIR, exist_ok=True)


# ========================
# 请求验证和日志中间件
# ========================

@app.before_request
def before_request_middleware():
    """请求前验证和日志记录"""
    # 记录请求基本信息
    logging.info(
        f"[请求] {request.method} {request.path} | "
        f"来源IP: {request.remote_addr} | "
        f"Content-Type: {request.headers.get('Content-Type', 'N/A')} | "
        f"User-Agent: {request.headers.get('User-Agent', 'N/A')[:50]}"
    )

    # 跳过健康检查端点的验证
    if request.path == '/healthz':
        return None

    # 对于 POST 请求，验证 Content-Type
    if request.method == 'POST' and request.path.startswith('/api/'):
        content_type = request.headers.get('Content-Type', '')

        # 验证 Content-Type 必须包含 application/json
        if 'application/json' not in content_type:
            logging.warning(
                f"[请求被拒绝] 无效的 Content-Type: '{content_type}' | "
                f"路径: {request.path} | 来源: {request.remote_addr} | "
                f"期望: application/json"
            )
            return jsonify({
                "code": 400,
                "msg": "Invalid Content-Type",
                "detail": "Content-Type must be 'application/json'",
                "received": content_type
            }), 400

        # 记录请求体大小
        content_length = request.headers.get('Content-Length', '0')
        logging.info(f"[请求体] 大小: {content_length} bytes")

        # 可选：限制请求体大小（例如 10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        try:
            if int(content_length) > max_size:
                logging.warning(
                    f"[请求被拒绝] 请求体过大: {content_length} bytes | "
                    f"最大允许: {max_size} bytes | 路径: {request.path}"
                )
                return jsonify({
                    "code": 413,
                    "msg": "Payload Too Large",
                    "detail": f"Request body exceeds maximum size of {max_size} bytes",
                    "size": int(content_length)
                }), 413
        except ValueError:
            pass  # Content-Length 不是有效数字，忽略


@app.after_request
def after_request_middleware(response):
    """响应后日志记录"""
    # 计算响应大小
    response_size = response.content_length or 0
    if response_size == 0 and hasattr(response, 'get_data'):
        try:
            response_size = len(response.get_data())
        except Exception:
            response_size = 0

    logging.info(
        f"[响应] {request.method} {request.path} | "
        f"状态码: {response.status_code} | "
        f"响应大小: {response_size} bytes"
    )
    return response


def _public_ip_from_request() -> str:
    # 优先使用环境变量（容器/云环境建议配置）
    public_ip = os.getenv("PUBLIC_IP")
    if public_ip:
        return public_ip
    # 回退：从请求 Host 解析（开发/内网调试可用）
    host = request.host.split(":")[0]
    return host or "127.0.0.1"


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})

# ========================
# 2) 基于现有 AI 服务的 HTTP 封装（如果可用）
# ========================


@app.post("/api/ai/message")
def api_ai_message():
    if not AI_AVAILABLE:
        logging.error("[API: message] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法处理 message"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: message] session_id: {session_id} | "
            f"消息条数: {len(llm_content)}"
        )

        # 使用统一的 handle_chat 接口（返回的是 JSON 字符串）
        logging.debug("[API: message] 调用 handle_integrated_entrance...")
        result_str = handle_integrated_entrance(payload)
        logging.info(f"[API: message] 处理成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: message] 处理失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-image")
def api_ai_generate_image():
    if not AI_AVAILABLE:
        logging.error("[API: generate-image] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成图片"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: generate-image] session_id: {session_id} | "
            f"llm_content 条数: {len(llm_content)}"
        )

        # 详细记录 llm_content 的结构（用于调试）
        if llm_content:
            for idx, content in enumerate(llm_content):
                parts = content.get("part", [])
                logging.debug(f"[API: generate-image] llm_content[{idx}] | part 条数: {len(parts)}")
                for part_idx, part in enumerate(parts):
                    content_type = part.get("content_type", "")
                    content_text = part.get("content_text", "")[:50]  # 只记录前50字符
                    content_url = part.get("content_url", "")
                    if content_text or content_url:
                        logging.debug(
                            f"[API: generate-image]   part[{part_idx}] | type: {content_type} | "
                            f"text: '{content_text}' | url: {'有' if content_url else '无'}"
                        )

        logging.debug("[API: generate-image] 调用 handle_image_generation...")
        result_str = handle_image_generation(payload)
        logging.info(f"[API: generate-image] 生成成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: generate-image] 生成失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-video")
def api_ai_generate_video():
    """图生视频 API"""
    if not AI_AVAILABLE:
        logging.error("[API: generate-video] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成视频"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: generate-video] session_id: {session_id} | "
            f"llm_content 条数: {len(llm_content)}"
        )

        logging.debug("[API: generate-video] 调用 handle_video_generation...")
        result_str = handle_video_generation(payload)
        logging.info(f"[API: generate-video] 生成成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: generate-video] 生成失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-text")
def api_ai_generate_text():
    """文案生成 API（产品/营销/创意文案）"""
    if not AI_AVAILABLE:
        logging.error("[API: generate-text] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成文案"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: generate-text] session_id: {session_id} | "
            f"llm_content 条数: {len(llm_content)}"
        )

        logging.debug("[API: generate-text] 调用 handle_text_generation...")
        result_str = handle_text_generation(payload)
        logging.info(f"[API: generate-text] 生成成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: generate-text] 生成失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-speech")
def api_ai_generate_speech():
    """TTS 语音合成 API"""
    if not AI_AVAILABLE:
        logging.error("[API: generate-speech] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成语音"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: generate-speech] session_id: {session_id} | "
            f"llm_content 条数: {len(llm_content)}"
        )

        logging.debug("[API: generate-speech] 调用 handle_speech_generation...")
        result_str = handle_speech_generation(payload)
        logging.info(f"[API: generate-speech] 生成成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: generate-speech] 生成失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-music")
def api_ai_generate_music():
    """BGM 音乐生成 API"""
    if not AI_AVAILABLE:
        logging.error("[API: generate-music] AI 服务未加载")
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成音乐"}), 503

    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
        session_id = payload.get("session_id", "未知")
        llm_content = payload.get("llm_content", [])

        logging.info(
            f"[API: generate-music] session_id: {session_id} | "
            f"llm_content 条数: {len(llm_content)}"
        )

        logging.debug("[API: generate-music] 调用 handle_music_generation...")
        result_str = handle_music_generation(payload)
        logging.info(f"[API: generate-music] 生成成功 | session_id: {session_id}")
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception(
            f"[API: generate-music] 生成失败 | session_id: {payload.get('session_id', '未知')} | "
            f"错误: {e}"
        )
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


if __name__ == "__main__":
    # 监听所有网卡，端口可通过环境变量 PORT 覆盖（默认5000）
    port = int(os.getenv("PORT", "20100"))
    app.run(host="0.0.0.0", port=port, debug=False)
