"""
客户端运行器模块
专门为 C++ 集成提供的 Python 接口
"""
import os
import sys
import queue
from pathlib import Path

# ========== 初始化路径 ==========
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from config.app_config import get_app_config
app_config = get_app_config()

# ========== 设置环境变量 ==========
if not app_config.runtime.enable_gpu:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --enable-logging=stderr"
    os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ['QT_OPENGL'] = 'software'
    os.environ["QT_DISABLE_DIRECT_COMPOSITION"] = "1"
    print("GPU 已禁用 - 使用软件渲染模式")

sys.path.append(str(app_config.paths.repo_root))

# ========== 全局状态 ==========
msg_queue = queue.Queue()
_client_app = None
_script_runner = None
_initialized = False


def initialize():
    """
    初始化客户端环境

    必须在调用 run() 之前调用一次
    可以重复调用(内部有防重复机制)

    Raises:
        RuntimeError: 初始化失败时抛出异常
    """
    global _client_app, _script_runner, _initialized

    if _initialized:
        print("Client already initialized, skipping...")
        return

    print("Initializing client environment...")

    try:
        # 1. 创建 Qt 应用
        from Backend.window_layout import main_window
        from Backend.utils.core.cleanup import cleanup_blockly_files
        from Backend.utils.gui.script_runner import ScriptRunner

        _client_app, window = main_window.init_app()
        _script_runner = ScriptRunner(_client_app)

        cleanup_blockly_files()
        _initialized = True
        print("✓ Client initialized successfully.")

    except Exception as e:
        print(f"✗ Client initialization failed: {e}")
        raise RuntimeError(f"客户端初始化失败: {e}")


def run(is_reload: bool = False):
    """
    执行一帧的客户端逻辑(供 C++ 每帧调用)

    Args:
        is_reload: 是否清除脚本缓存(用于热重载)

    Raises:
        RuntimeError: 未初始化或执行失败时抛出异常

    Example:
        # C++ 代码示例
        // 初始化阶段(只需调用一次)
        PyObject* pInitFunc = PyObject_GetAttrString(pModule, "initialize");
        PyObject_CallObject(pInitFunc, NULL);

        // 游戏主循环
        PyObject* pRunFunc = PyObject_GetAttrString(pModule, "run");
        while (running) {
            PyObject* pArgs = Py_BuildValue("(O)", Py_False);
            PyObject_CallObject(pRunFunc, pArgs);
            Py_DECREF(pArgs);
        }
    """
    global _client_app, _script_runner

    # 自动初始化(如果尚未初始化)
    if not _initialized:
        initialize()

    if _script_runner is None or _client_app is None:
        raise RuntimeError("客户端环境未正确初始化")

    try:
        # 1. 热重载逻辑
        if is_reload:
            from Backend.utils.core.hot_reload import clear_script_modules
            clear_script_modules()

        # 2. 执行脚本
        _script_runner.load_and_run()

        # 3. 处理 Qt 事件队列
        _client_app.processEvents()

        # 4. 处理消息队列
        if not msg_queue.empty():
            msg = msg_queue.get()
            print(msg)

    except Exception as e:
        print(f"✗ Run frame failed: {e}")
        # 不抛出异常,避免中断 C++ 主循环
        _client_app.processEvents()


def shutdown():
    """
    清理资源(C++ 程序退出前调用)
    """
    global _initialized, _client_app, _script_runner

    if not _initialized:
        return

    print("Shutting down client...")

    try:
        if _client_app is not None:
            _client_app.quit()
    except Exception as e:
        print(f"✗ Shutdown error: {e}")
    finally:
        _initialized = False
        _client_app = None
        _script_runner = None
        print("✓ Client shutdown complete.")


def put_queue(msg: str):
    """
    将消息放入队列(线程安全)

    Args:
        msg: 要输出的消息内容
    """
    msg_queue.put(msg)


def is_initialized() -> bool:
    """
    检查客户端是否已初始化

    Returns:
        bool: 已初始化返回 True,否则返回 False
    """
    return _initialized


# ========== 仅用于测试 ==========
def _test_main_loop():
    """
    Python 测试入口(模拟 C++ 调用)
    """
    print("Starting Python test loop...")
    initialize()

    frame_count = 0
    try:
        while True:
            run(is_reload=False)
            frame_count += 1

            if frame_count % 60 == 0:
                print(f"Frame: {frame_count}")

    except KeyboardInterrupt:
        print("\n程序正常退出")
    finally:
        shutdown()


if __name__ == '__main__':
    _test_main_loop()
