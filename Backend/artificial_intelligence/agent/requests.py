from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass(frozen=True)
class ImageAttachment:
    name: str
    category: str
    data: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class IncomingRequest:
    session_id: str
    text: str
    images: List[ImageAttachment]


def normalize_request(raw: Any, default_session: str) -> IncomingRequest:
    if isinstance(raw, IncomingRequest):
        return raw
    session_id = default_session
    if isinstance(raw, str):
        return IncomingRequest(session_id=session_id, text=raw, images=[])
    if isinstance(raw, dict):
        text = str(raw.get("message", "") or "")
        session_id = str(raw.get("session_id") or session_id)
        images = coerce_images(raw.get("images"))
        return IncomingRequest(session_id=session_id, text=text, images=images)
    return IncomingRequest(session_id=session_id, text=str(raw), images=[])


def coerce_images(value: Any) -> List[ImageAttachment]:
    if not isinstance(value, list):
        return []
    attachments: List[ImageAttachment] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        attachments.append(
            ImageAttachment(
                name=str(entry.get("name") or "image"),
                category=str(entry.get("type") or "product"),
                data=str(entry.get("data")) if entry.get("data") else None,
                url=str(entry.get("url")) if entry.get("url") else None,
            )
        )
    return attachments


__all__ = [
    "ImageAttachment",
    "IncomingRequest",
    "normalize_request",
    "coerce_images",
]
