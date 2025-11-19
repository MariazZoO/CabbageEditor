from __future__ import annotations

from .scene_service import SceneApplicationService
from .project_service import ProjectApplicationService
from Backend.engine_core.managers import scene_manager as scene_manager_module
from Backend.utils.container import get_container
from Backend.utils.logging import configure_logging


def bootstrap() -> None:
    container = get_container()
    if container.get_flag("bootstrapped"):
        return
    configure_logging()

    container.register("scene_manager", lambda: scene_manager_module)
    container.register("scene_service", lambda: SceneApplicationService(container.resolve("scene_manager")))
    container.register(
        "project_service",
        lambda: ProjectApplicationService(container.resolve("scene_service")),
    )
    container.set_flag("bootstrapped", True)


__all__ = ["bootstrap"]
