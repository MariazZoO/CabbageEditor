from __future__ import annotations
import os
import json
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication


class AppService(QObject):
    create_route_requested = Signal(str, str, str, str, object)
    remove_route_requested = Signal(str)
    message_to_dock_requested = Signal(str, str)
    command_to_main_requested = Signal(str, str)

    @Slot(str, str, str, str, str)
    def add_dock_widget(self, routename: str, routepath: str, position: str = "left", floatposition: str = "None",
                        size: str | None = None) -> None:
        try:
            size_obj = json.loads(size) if isinstance(size, str) and size else None
        except json.JSONDecodeError:
            size_obj = None
        self.create_route_requested.emit(routename, routepath, position, floatposition, size_obj)

    # Provide a convenience alias method name
    add_dock = add_dock_widget

    @Slot(str)
    def remove_dock_widget(self, routename: str) -> None:
        self.remove_route_requested.emit(routename)

    # alias
    remove_dock = remove_dock_widget

    @Slot(str, str)
    def send_message_to_dock(self, routename: str, json_data: str) -> None:
        self.message_to_dock_requested.emit(routename, json_data)

    @Slot(str, str)
    def send_command_to_main(self, command_name: str, command_data: str) -> None:
        self.command_to_main_requested.emit(command_name, command_data)

    @Slot()
    def close_process(self) -> None:
        QApplication.quit()
        os._exit(0)

    @Slot(str, str)
    def send_message_to_main(self, command_name: str, command_data: str) -> None:
        self.command_to_main_requested.emit(command_name, command_data)

    # alias for clarity
    send_command = send_message_to_main
    send_message = send_message_to_main
