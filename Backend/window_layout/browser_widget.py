import json

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from Backend.utils import CentralManager
from Backend.frontend_bridge import setup_webchannel_for_view, teardown_webchannel_for_view



class BrowserWidget(QWebEngineView):
    input_code_signal = Signal(str)
    def __init__(self, Main_Window, url: QUrl):
        super(BrowserWidget, self).__init__(Main_Window)
        self.Main_Window = Main_Window
        self.central_manager = CentralManager(Main_Window)
        self._webchannel_ctx = None

        self.url = QUrl(url) if isinstance(url, str) else url

        self.setMinimumSize(1, 1)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))
        self.load(self.url)
        self.setContentsMargins(0, 0, 0, 0)

        self.setup_web_channel()

    def setup_web_channel(self):
        # 通过回调直接接 appService 信号
        self._webchannel_ctx = setup_webchannel_for_view(
            self,
            self.central_manager,
            register_services=True,
            on_create_route=self.central_manager.create_dock,
            on_remove_route=self.central_manager.remove_dock,
            on_message_to_dock=lambda name, data: self.central_manager.send_json_to_dock(name, data),
            on_command_to_main=self.handle_command_to_main,
        )

    def handle_command_to_main(self, command_name, command_data):
        if command_name == "go_home":
            self.load(self.url)
            return

        if command_name == "input_event":
            try:
                payload = json.loads(command_data) if isinstance(command_data, str) else command_data
            except Exception:
                payload = command_data
            try:
                kind = payload.get('kind', '?') if isinstance(payload, dict) else '?'
                etype = payload.get('type', '?') if isinstance(payload, dict) else '?'
                key = payload.get('key', '?') if isinstance(payload, dict) else '?'
                code = payload.get('code', '?') if isinstance(payload, dict) else '?'
                cx = payload.get('clientX') if isinstance(payload, dict) else None
                cy = payload.get('clientY') if isinstance(payload, dict) else None
                print(f"[input_event] kind={kind} type={etype} key={key} code={code} pos=({cx},{cy})")
                # 向 Python 侧（Blockly 生成脚本）广播键盘按键信号（如已订阅）
                if code not in (None, '?'):
                    try:
                        self.input_code_signal.emit(str(code))
                    except Exception:
                        pass
            except Exception:
                print(f"[input_event] raw={command_data}")
            return
        return

    def closeEvent(self, event):
        try:

            if getattr(self, "_webchannel_ctx", None):
                teardown_webchannel_for_view(self, self._webchannel_ctx)
                self._webchannel_ctx = None
        finally:
            super().closeEvent(event)
