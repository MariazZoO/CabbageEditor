from __future__ import annotations

import json
from typing import Literal, TYPE_CHECKING, Tuple, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from Backend.utils import SceneApplicationService


class SceneQueryInput(BaseModel):
    scene_name: str = Field(default="MainScene", description="要查询的场景名称")
    query: Literal["list_models", "get_model_by_name"] = Field(description="查询类型")
    name: str | None = Field(default=None, description="当 query=get_model_by_name 时需要提供模型名")


class TransformModelInput(BaseModel):
    scene_name: str = Field(default="MainScene", description="目标场景名称")
    model_name: str = Field(description="需要变换的模型名称")
    operation: Literal["scale", "move", "rotate"] = Field(default="scale", description="变换类型")
    scale_factor: float | None = Field(
        default=None,
        description="当 operation=scale 时的倍率（例如 2 表示放大两倍）",
    )
    vector: Tuple[float, float, float] | None = Field(
        default=None,
        description="当 operation=move/rotate 时的 (x,y,z) 向量；"
        "若 operation=scale 且未提供 scale_factor，可用该向量表示各轴缩放。",
    )


def _build_scene_query_tool(scene_service: "SceneApplicationService") -> StructuredTool:
    def _query_scene(
        *,
        scene_name: str = "MainScene",
        query: Literal["list_models", "get_model_by_name"],
        name: str | None = None,
    ) -> str:
        data = SceneQueryInput(scene_name=scene_name, query=query, name=name)
        scene = scene_service.get_scene(data.scene_name)
        if scene is None:
            return json.dumps({"scene": data.scene_name, "actors": []}, ensure_ascii=False)

        if data.query == "list_models":
            actors = [actor.name for actor in scene.get_actors()]
            return json.dumps({"scene": data.scene_name, "actors": actors}, ensure_ascii=False)

        if data.query == "get_model_by_name":
            actor = scene_service._find_actor(scene, data.name or "")
            if actor is None:
                return json.dumps(
                    {"scene": data.scene_name, "actor": None, "found": False},
                    ensure_ascii=False,
                )
            return json.dumps(
                {"scene": data.scene_name, "actor": actor.name, "path": actor.path, "found": True},
                ensure_ascii=False,
            )

        raise ValueError(f"Unsupported query type: {data.query}")

    return StructuredTool(
        name="scene_query",
        description="查询场景中的模型，例如列出全部模型或按名称查找。",
        args_schema=SceneQueryInput,
        func=_query_scene,
    )


def _build_transform_tool(scene_service: "SceneApplicationService") -> StructuredTool:
    def _transform_model(
        *,
        scene_name: str = "MainScene",
        model_name: str,
        operation: Literal["scale", "move", "rotate"] = "scale",
        scale_factor: float | None = None,
        vector: Tuple[float, float, float] | None = None,
    ) -> str:
        data = TransformModelInput(
            scene_name=scene_name,
            model_name=model_name,
            operation=operation,
            scale_factor=scale_factor,
            vector=vector,
        )
        op = data.operation.lower()
        if op == "scale":
            if data.scale_factor is not None:
                vector = [data.scale_factor] * 3
            elif data.vector is not None:
                vector = list(data.vector)
            else:
                raise ValueError("scale 操作需要提供 scale_factor 或 vector")
            payload = scene_service.apply_transform(data.scene_name, data.model_name, "Scale", vector)
        elif op == "move":
            if data.vector is None:
                raise ValueError("move 操作需要提供 vector")
            payload = scene_service.apply_transform(data.scene_name, data.model_name, "Move", list(data.vector))
        elif op == "rotate":
            if data.vector is None:
                raise ValueError("rotate 操作需要提供 vector")
            payload = scene_service.apply_transform(data.scene_name, data.model_name, "Rotate", list(data.vector))
        else:
            raise ValueError(f"Unsupported operation '{data.operation}'")

        return json.dumps(payload, ensure_ascii=False)

    return StructuredTool(
        name="transform_model",
        description="对模型执行缩放/移动/旋转等操作。默认操作为放大或缩小。",
        args_schema=TransformModelInput,
        func=_transform_model,
    )


def load_scene_tools(scene_service: "SceneApplicationService") -> List[StructuredTool]:
    return [
        _build_scene_query_tool(scene_service),
        _build_transform_tool(scene_service),
    ]


__all__ = ["load_scene_tools"]
