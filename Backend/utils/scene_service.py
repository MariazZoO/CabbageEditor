from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ..engine_core.entities.actor import Actor
from ..engine_core.managers.scene_manager import SceneManager
from .logging import (get_logger)


logger = get_logger(__name__)


def _actor_payload(actor: Actor) -> Dict[str, str]:
    _, ext = os.path.splitext(actor.path)
    return {
        "name": actor.name,
        "path": actor.path,
        "type": ext.lstrip("."),
    }


def _scene_snapshot(scene) -> Dict[str, Any]:
    return {
        "name": scene.name,
        "sun_direction": getattr(scene, "sun_direction", [0.0, -1.0, 0.0]),
        "actors": [_actor_payload(actor) for actor in scene.get_actors()],
        "cameras": [{"name": getattr(camera, "name", "")} for camera in scene.get_cameras()],
        "lights": [{"name": getattr(light, "name", "")} for light in scene.get_lights()],
    }


class SceneApplicationService:
    def __init__(self, scene_manager: SceneManager | None = None) -> None:
        self.scene_manager = scene_manager or SceneManager()

    def _get_scene(self, scene_name: str):
        scene = self.scene_manager.get_scene(scene_name)
        if scene is None:
            raise ValueError(f"Scene '{scene_name}' not found")
        return scene

    def create_scene(self, scene_name: str) -> Dict:
        scene = self.scene_manager.create_scene(scene_name)
        logger.info("Created scene %s", scene_name)
        return _scene_snapshot(scene)

    def add_actor(self, scene_name: str, asset_path: str) -> Dict:
        scene = self._get_scene(scene_name)
        actor = Actor(asset_path)
        scene.add_actor(actor)
        payload = {"scene": scene_name, "actor": _actor_payload(actor)}
        logger.info("Actor %s added to %s", actor.name, scene_name)
        return payload

    def remove_actor(self, scene_name: str, actor_name: str) -> Dict:
        scene = self._get_scene(scene_name)
        actor = self._find_actor(scene, actor_name)
        if actor is None:
            raise ValueError(f"Actor '{actor_name}' not found")
        scene.remove_actor(actor)
        logger.info("Actor %s removed from %s", actor_name, scene_name)
        return {"scene": scene_name, "actor": actor_name}

    def apply_transform(self, scene_name: str, actor_name: str, operation: str, vector: List[float]) -> Dict:
        scene = self._get_scene(scene_name)
        actor = self._find_actor(scene, actor_name)
        if actor is None:
            raise ValueError(f"Actor '{actor_name}' not found")
        if operation == "Scale":
            actor.set_scale(vector)
        elif operation == "Move":
            actor.set_position(vector)
        elif operation == "Rotate":
            actor.set_rotation(vector)
        else:
            raise ValueError(f"Unsupported operation '{operation}'")
        logger.debug("Applied %s%s to %s", operation, vector, actor_name)
        return {"scene": scene_name, "actor": actor_name, "operation": operation, "vector": vector}

    def set_camera(self, scene_name: str, *, position, forward, up, fov: float) -> None:
        scene = self._get_scene(scene_name)
        if hasattr(scene, "set_camera"):
            scene.set_camera(position, forward, up, fov)
        logger.debug("Camera updated in %s", scene_name)

    def set_sun(self, scene_name: str, direction: List[float]) -> None:
        scene = self._get_scene(scene_name)
        scene.set_sun_direction(direction)
        logger.debug("Sun direction set for %s", scene_name)

    def _find_actor(self, scene, actor_name: str | None):
        if not actor_name:
            return None
        actor = scene.get_actor(actor_name)
        if actor:
            return actor
        normalized = self._normalize_actor_name(actor_name)
        for candidate in scene.get_actors():
            if self._normalize_actor_name(candidate.name) == normalized:
                return candidate
        return None

    @staticmethod
    def _normalize_actor_name(name: str) -> str:
        value = name.strip().strip('"').strip("'")
        base = os.path.splitext(value.lower())[0]
        return base

    def export_scene(self, scene_name: str) -> str:
        scene = self._get_scene(scene_name)
        return json.dumps(_scene_snapshot(scene), indent=2)
