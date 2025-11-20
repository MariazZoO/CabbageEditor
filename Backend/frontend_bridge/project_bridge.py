from __future__ import annotations
import json
from PySide6.QtCore import QObject, Signal, Slot

from Backend.utils import ProjectApplicationService, get_project_service
from Backend.utils import FileHandler
from .scene_bridge import SceneService


class ProjectService(QObject):
    scene_saved = Signal(str)
    scene_loaded = Signal(str)

    def __init__(self, scene_service: SceneService | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.project_service: ProjectApplicationService = get_project_service()
        self.scene_service = scene_service
        self.file_handler = FileHandler()

    def _emit_actor_created(self, payload: str) -> None:
        if not self.scene_service:
            return
        try:
            data = json.loads(payload)
            actor = data.get("actor")
            if not actor:
                return
            message = json.dumps(
                {
                    "name": actor.get("name"),
                    "path": actor.get("path"),
                    "type": actor.get("type"),
                }
            )
            self.scene_service.actor_created.emit(message)
        except Exception:
            pass

    @Slot(str, str)
    def open_file_dialog(self, scene_name: str, file_type: str = "model") -> None:
        try:
            if file_type == "model":
                _, file_path = self.file_handler.open_file("选择模型文件", "3D模型文件 (*.obj *.fbx *.dae)")
                if file_path:
                    payload = self.project_service.import_model(scene_name, file_path)
                    self.scene_loaded.emit(payload)
                    self._emit_actor_created(payload)
            elif file_type == "scene":
                content, file_path = self.file_handler.open_file("选择场景文件", "场景文件 (*.json)")
                if file_path and content:
                    payload = self.project_service.import_scene_file(scene_name, content)
                    self.scene_loaded.emit(payload)
            elif file_type == "multimedia":
                _, file_path = self.file_handler.open_file("选择多媒体文件", "多媒体文件 (*.mp4 *.avi *.mov *.mp3 *.wav)")
                if file_path:
                    payload = self.project_service.import_model(scene_name, file_path)
                    self.scene_loaded.emit(payload)
                    self._emit_actor_created(payload)
        except Exception as exc:
            self.scene_loaded.emit(json.dumps({"status": "error", "message": str(exc)}))

    @Slot(str)
    def scene_save(self, data: str) -> None:
        try:
            payload = json.loads(data)
            content = json.dumps(payload, indent=2)
            save_path = self.file_handler.save_file(content, "保存场景文件", "场景文件 (*.json)")
            status = {"status": "success", "filepath": save_path} if save_path else {"status": "error", "filepath": save_path}
            self.scene_saved.emit(json.dumps(status))
        except Exception as exc:
            self.scene_saved.emit(json.dumps({"status": "error", "message": str(exc)}))

