import os
import sys
import queue
from pathlib import Path

# 1. 设置项目根目录路径
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# 2. 加载全局配置
from config.app_config import get_app_config
app_config = get_app_config()

# 3. 设置环境变量（必须在导入 Qt 之前）
if not app_config.runtime.enable_gpu:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --enable-logging=stderr"
    os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ['QT_OPENGL'] = 'software'
    os.environ["QT_DISABLE_DIRECT_COMPOSITION"] = "1"
    print("GPU 已禁用 - 使用软件渲染模式")

# 确保 repo_root 在 sys.path 中
sys.path.append(str(app_config.paths.repo_root))


def main():
    """
    统一的应用入口
    支持服务端和客户端两种模式
    """
    # 优先从环境变量读取 APP_MODE，这对于 Docker 部署至关重要
    app_mode = os.environ.get('APP_MODE', 'client').lower()

    print(f"--- Starting application in {app_mode.upper()} mode ---")

    # 根据模式选择执行逻辑
    if app_mode == 'server':
        # 服务器模式：启动 AI 服务的 HTTP API
        from Backend.network_service.server import app

        host = os.environ.get('SERVER_HOST', '0.0.0.0')
        port = os.environ.get('SERVER_PORT', '20100')

        print(f"Starting server at {host}:{port}")

        # 使用 Gunicorn（生产环境）
        try:
            from gunicorn.app.base import BaseApplication

            class StandaloneApplication(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            options = {
                'bind': f'{host}:{port}',
                'workers': 4,
                'timeout': 120,
                'accesslog': '-',
                'errorlog': '-',
            }
            StandaloneApplication(app, options).run()
        except ImportError:
            # 回退到 Flask 开发服务器
            app.run(host=host, port=port, debug=False)

    elif app_mode == 'client':
        # 客户端模式：启动 Qt 桌面应用
        print(f"Running in CLIENT mode. Starting Qt application...")

        # 启动 Qt 应用
        from Backend.window_layout import main_window
        from Backend.utils.cleanup import cleanup_blockly_files
        from Backend.utils.script_runner import ScriptRunner
        app, window = main_window.init_app()
        script_runner = ScriptRunner(app)

        print("Qt application started.")
        cleanup_blockly_files()
        while True:
            script_runner.load_and_run()
            app.processEvents()

    else:
        print(f"Error: Unknown mode '{app_mode}'. Please use 'server' or 'client'.", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
