import unittest
import json
from unittest.mock import patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# 假设您的项目结构如下，请根据实际情况调整 import 路径
# 模拟环境导入
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from Backend.artificial_intelligence.service.integrated import handle_integrated_entrance
from Backend.artificial_intelligence.agent.interface import process_chat_request


class TestAttachmentFunctionality(unittest.TestCase):

    # =========================================================================
    # 测试点 1: 检查输入端 (Input)
    # 验证：用户输入的图片/音频是否被转换成了 ToolMessage，且顺序在 HumanMessage 之前
    # =========================================================================
    @patch("Backend.artificial_intelligence.agent.interface.run_agent")
    @patch("Backend.artificial_intelligence.agent.interface.get_history")
    @patch("Backend.artificial_intelligence.agent.interface.extract_session_id")
    def test_input_attachment_injection(self, mock_extract_id, mock_get_history, mock_run_agent):
        # --- 准备 ---
        mock_extract_id.return_value = "test_sess_001"
        mock_get_history.return_value = []  # 假设没有历史记录
        mock_run_agent.return_value = {"messages": []}  # Mock返回，我们只关心输入参数

        # 构造输入 Payload: 1个文本 + 1个图片 + 1个音频
        payload = {
            "session_id": "test_sess_001",
            "llm_content": [
                {
                    "role": "user",
                    "part": [
                        {"content_type": "image", "content_url": "http://test.com/img.png"},
                        {
                            "content_type": "audio",
                            "content_url": "http://test.com/audio.mp3",
                            "parameter": {"duration": 10},
                        },
                        {"content_type": "text", "content_text": "分析这些附件"},
                    ],
                }
            ],
        }

        # --- 执行 ---
        process_chat_request(payload)

        # --- 验证 ---
        # 获取调用 run_agent 时传入的参数 (pending_history)
        args, _ = mock_run_agent.call_args
        pending_history = args[0]

        print("\n[Input Check] History Structure:")
        for i, msg in enumerate(pending_history):
            print(f"  {i}. {type(msg).__name__}: {msg.content[:50]}...")

        # 断言 1: 历史记录应该有 3 条 (ImageTool, AudioTool, HumanText)
        self.assertEqual(len(pending_history), 3)

        # 断言 2: 前两条必须是 ToolMessage (伪造的附件)
        self.assertIsInstance(pending_history[0], ToolMessage)
        self.assertIsInstance(pending_history[1], ToolMessage)
        self.assertEqual(pending_history[0].name, "upload_attachment_tool")

        # 断言 3: 最后一条必须是 HumanMessage (文本)
        self.assertIsInstance(pending_history[2], HumanMessage)
        self.assertEqual(pending_history[2].content[0]["text"], "分析这些附件")

        # 断言 4: 检查 Session ID 是否注入到了伪造工具消息中
        tool_content = json.loads(pending_history[0].content)
        self.assertEqual(tool_content["session_id"], "test_sess_001")
        self.assertEqual(
            tool_content["llm_content"][0]["part"][0]["content_url"], "http://test.com/img.png"
        )
        print("✅ 输入端验证通过：附件已正确转换为前置工具消息。")

    # =========================================================================
    # 测试点 2: 检查输出端 (Output)
    # 验证：Tool 产生的媒体是否吸附到 Assistant 上，且顺序为 [Text, Media]
    # =========================================================================
    @patch("Backend.artificial_intelligence.service.integrated.process_chat_request")
    def test_output_media_adsorption_order(self, mock_process):
        # --- 准备 ---
        # 模拟 Tool 返回的完整 Envelope (图片)
        tool_envelope = {
            "session_id": "test_sess_002",
            "error_code": 0,
            "status_info": "ok",
            "llm_content": [
                {
                    "role": "tool",
                    "part": [
                        {
                            "content_type": "image",
                            "content_url": "http://gen.com/art.jpg",
                        }
                    ],
                }
            ],
        }

        # 模拟 Agent 的执行轨迹: AIMessage -> ToolMessage
        mock_messages = [
            AIMessage(content="图片已生成。"),
            ToolMessage(content=json.dumps(tool_envelope), tool_call_id="call_x", name="gen_img"),
        ]

        mock_process.return_value = {
            "messages": mock_messages,
            "session_id": "test_sess_002",
            "pending_history": [],
        }

        payload = {
            "session_id": "test_sess_002",
            "llm_content": [
                {"role": "user", "part": [{"content_type": "text", "content_text": "dummy input"}]}
            ],
        }

        # --- 执行 ---
        response_str = handle_integrated_entrance(payload)
        response = json.loads(response_str)

        # --- 验证 ---
        assistant_msg = response["llm_content"][0]
        parts = assistant_msg["part"]

        print("\n[Output Check] Parts Order:")
        for i, p in enumerate(parts):
            print(
                f"  {i}. Type: {p['content_type']} | Content: {p.get('content_text') or p.get('content_url')}"
            )

        # 断言 1: 必须吸附在一起，共 2 个 part
        self.assertEqual(len(parts), 2)

        # 断言 2: [关键] 验证顺序 —— 您要求的是先 Text 后 Media
        # Part 0 应该是 Text
        self.assertEqual(parts[0]["content_type"], "text")
        self.assertEqual(parts[0]["content_text"], "图片已生成。")

        # Part 1 应该是 Image
        self.assertEqual(parts[1]["content_type"], "image")
        self.assertEqual(parts[1]["content_url"], "http://gen.com/art.jpg")

        print("✅ 输出端验证通过：顺序正确 (Text -> Media)。")


if __name__ == "__main__":
    unittest.main()
