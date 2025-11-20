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
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法处理 message"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        # 使用统一的 handle_chat 接口（返回的是 JSON 字符串）
        result_str = handle_integrated_entrance(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/message 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-image")
def api_ai_generate_image():
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成图片"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        result_str = handle_image_generation(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/generate-image 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/upload-image")
def api_ai_upload_image():
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法上传图片"}), 503
    try:
        if "file" not in request.files:
            return jsonify({"code": 400, "msg": "缺少文件字段 'file' (multipart/form-data)"}), 400
        f = request.files["file"]
        import base64
        data = base64.b64encode(f.read()).decode('utf-8')
        category = request.form.get("category") or "product"
        message = request.form.get("message") or ""
        session_id = request.form.get("session_id") or None
        
        # 使用统一的 handle_integrated_entrance 接口格式
        payload = {
            "message": message,
            "images": [
                {
                    "name": f.filename or "upload.bin",
                    "type": category,
                    "data": data
                }
            ]
        }
        if session_id:
            payload["session_id"] = session_id
        
        result_str = handle_integrated_entrance(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/upload-image 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-video")
def api_ai_generate_video():
    """图生视频 API"""
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成视频"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        result_str = handle_video_generation(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/generate-video 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-text")
def api_ai_generate_text():
    """文案生成 API（产品/营销/创意文案）"""
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成文案"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        result_str = handle_text_generation(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/generate-text 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-speech")
def api_ai_generate_speech():
    """TTS 语音合成 API"""
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成语音"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        result_str = handle_speech_generation(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/generate-speech 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


@app.post("/api/ai/generate-music")
def api_ai_generate_music():
    """BGM 音乐生成 API"""
    if not AI_AVAILABLE:
        return jsonify({"code": 503, "msg": "AI 服务未加载，无法生成音乐"}), 503
    try:
        payload = request.get_json(silent=True) or {}
        result_str = handle_music_generation(payload)
        return Response(result_str, status=200, mimetype="application/json")
    except Exception as e:  # noqa: BLE001
        logging.exception("/api/ai/generate-music 失败: %s", e)
        return jsonify({"code": 500, "msg": f"服务器错误：{e}"}), 500


if __name__ == "__main__":
    # 监听所有网卡，端口可通过环境变量 PORT 覆盖（默认5000）
    port = int(os.getenv("PORT", "20100"))
    app.run(host="0.0.0.0", port=port, debug=False)
