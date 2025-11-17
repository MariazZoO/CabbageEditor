# ============================================================================
# Python 后端测试示例
# ============================================================================

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_image_generation_service():
    """测试图像生成服务的基本功能"""
    # 导入需要的模块
    import json
    from PySide6.QtCore import QCoreApplication
    from Backend.utils.bootstrap import bootstrap
    from Backend.frontend_bridge.image_generation_bridge import ImageGenerationService
    # 确保 bootstrap 已执行
    bootstrap()

    app = QCoreApplication(sys.argv)

    # 创建服务实例
    service = ImageGenerationService()

    # 连接响应信号
    def on_response(response):
        data = json.loads(response)
        print("\n收到响应:")
        print(f"  状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"  提示词: {data.get('prompt')}")
            print(f"  图像名: {data['image']['name']}")
            print(f"  图像路径: {data['image']['path']}")
        else:
            print(f"  错误: {data.get('content')}")

        app.quit()

    service.image_generation_response.connect(on_response)

    # 发送测试请求
    payload = {"prompt": "一只可爱的奶牛猫", "session_id": "test_session"}

    print(f"发送请求: {payload}")
    service.generate_image(json.dumps(payload))

    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    # 运行测试（需要配置好图像生成 API）
    test_image_generation_service()

    # print(__doc__)
