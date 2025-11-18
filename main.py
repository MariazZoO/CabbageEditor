import os
import sys
import importlib.util
import glob
import queue
from pathlib import Path

# 1. 设置项目根目录路径
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# 2. 加载配置
from Backend.artificial_intelligence.config.config import get_app_config
app_config = get_app_config()

# 3. 设置环境变量（必须在导入 Qt 之前）
if not app_config.runtime.enable_gpu:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --enable-logging=stderr"
    os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ['QT_OPENGL'] = 'software'
    os.environ["QT_DISABLE_DIRECT_COMPOSITION"] = "1"
    print("GPU 已禁用 - 使用软件渲染模式")

sys.path.append(str(app_config.paths.repo_root))

# 4. 初始化核心服务
from Backend.utils.bootstrap import bootstrap
bootstrap()

# 5. 启动 Qt 应用
from Backend.window_layout import main_window  # noqa: E402

app, window = main_window.init_app()
msg_queue = queue.Queue()
_cleaned_up = False


def cleanup_blockly_files():
    """删除上次运行残留的 blockly 脚本与入口文件，避免热更新时导入冲突。"""
    global _cleaned_up
    if _cleaned_up:
        return

    current_dir = Path(__file__).parent
    runscript_path = current_dir / 'runScript.py'
    if runscript_path.exists():
        try:
            runscript_path.unlink()
            print(f"已删除: {runscript_path}")
        except PermissionError:
            print(f"无法删除 {runscript_path}，文件可能被占用")

    script_dir = current_dir / 'script'
    if script_dir.exists():
        for file in glob.glob(str(script_dir / 'blockly_code*.py')):
            try:
                Path(file).unlink()
                print(f"已删除: {file}")
            except PermissionError:
                print(f"无法删除 {file}，文件可能被占用")

    _cleaned_up = True


def run(isReload):
    """按需清理残留，热重载时清理模块缓存后调用 runScript.run()。"""
    global _cleaned_up
    if not _cleaned_up:
        cleanup_blockly_files()

    if isReload:
        for module_name in list(sys.modules.keys()):
            if 'runScript' in module_name or 'script' in module_name:
                del sys.modules[module_name]
        print("python hotfix")

    runscript_spec = importlib.util.find_spec("runScript")
    if runscript_spec is not None:
        runScript = importlib.util.module_from_spec(runscript_spec)
        runscript_spec.loader.exec_module(runScript)
        try:
            runScript.run()
        except Exception as e:
            print(f"runScript.run 执行失败: {e}")

    if not msg_queue.empty():
        print(msg_queue.get())

    app.processEvents()


def put_queue(msg):
    msg_queue.put(msg)


if __name__ == '__main__':
    cleanup_blockly_files()
    while True:
        try:
            runscript_spec = importlib.util.find_spec("runScript")
            if runscript_spec is not None:
                runScript = importlib.util.module_from_spec(runscript_spec)
                runscript_spec.loader.exec_module(runScript)
                try:
                    runScript.run()
                except Exception as e:
                    print(f"runScript.run 执行失败: {e}")
            app.processEvents()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"主循环异常: {e}")
            app.processEvents()
