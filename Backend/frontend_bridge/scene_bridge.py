from __future__ import annotations
import json
from PySide6.QtCore import QObject, Signal, Slot

from Backend.utils.scene_service import SceneApplicationService, get_scene_service



class SceneService(QObject):
    scene_error = Signal(str)
    actor_created = Signal(str)
    scene_loaded = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.scene_service: SceneApplicationService = get_scene_service()

    @Slot(str, str)
    def create_actor(self, scene_name: str, obj_path: str) -> None:
        try:
            payload = self.scene_service.add_actor(scene_name, obj_path)
            self.actor_created.emit(json.dumps(payload))
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))

    @Slot(str)
    def create_scene(self, data: str) -> None:
        try:
            scene_name = json.loads(data).get("sceneName")
            if not scene_name:
                raise ValueError("sceneName is required")
            self.scene_service.create_scene(scene_name)
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))

    @Slot(str, str)
    def remove_actor(self, scene_name: str, actor_name: str) -> None:
        try:
            self.scene_service.remove_actor(scene_name, actor_name)
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))

    @Slot(str)
    def actor_operation(self, data: str) -> None:
        try:
            actor_data = json.loads(data)
            payload = self.scene_service.apply_transform(
                actor_data.get("sceneName", "MainScene"),
                actor_data.get("actorName"),
                actor_data.get("Operation"),
                [
                    float(actor_data.get("x", 0.0)),
                    float(actor_data.get("y", 0.0)),
                    float(actor_data.get("z", 0.0)),
                ],
            )
            self.scene_loaded.emit(json.dumps({"type": "actor_operation", "data": payload}))
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))

    @Slot(str)
    def camera_move(self, data: str) -> None:
        try:
            move_data = json.loads(data)
            self.scene_service.set_camera(
                move_data.get("sceneName", "MainScene"),
                position=move_data.get("position", [0.0, 5.0, 10.0]),
                forward=move_data.get("forward", [0.0, 1.5, 0.0]),
                up=move_data.get("up", [0.0, -1.0, 0.0]),
                fov=float(move_data.get("fov", 45.0)),
            )
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))

    @Slot(str)
    def sun_direction(self, data: str) -> None:
        try:
            sun_data = json.loads(data)
            self.scene_service.set_sun(
                sun_data.get("sceneName", "MainScene"),
                [
                    float(sun_data.get("px", 1.0)),
                    float(sun_data.get("py", 1.0)),
                    float(sun_data.get("pz", 1.0)),
                ],
            )
        except Exception as exc:
            self.scene_error.emit(json.dumps({"type": "error", "message": str(exc)}))
