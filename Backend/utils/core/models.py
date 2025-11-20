from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict


@dataclass
class ProjectAsset:
    name: str
    path: Path
    type: str


@dataclass
class SceneDocument:
    name: str
    actors: List[ProjectAsset]

    def to_json(self) -> Dict:
        return {
            "name": self.name,
            "actors": [
                {"name": a.name, "path": str(a.path), "type": a.type}
                for a in self.actors
            ],
        }
