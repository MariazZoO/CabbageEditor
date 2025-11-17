from __future__ import annotations

from typing import Dict, List, Sequence
from langchain_core.messages import BaseMessage

from Backend.artificial_intelligence.tools.session import (
    get_boot_session_id,
    get_current_session,
)


class ConversationStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, List[BaseMessage]] = {}

    def snapshot(self, session_id: str) -> List[BaseMessage]:
        return list(self._sessions.get(session_id, []))

    def update(self, session_id: str, messages: Sequence[BaseMessage]) -> None:
        self._sessions[session_id] = list(messages)


_CONVERSATIONS = ConversationStore()


def get_history(session_id: str) -> List[BaseMessage]:
    return _CONVERSATIONS.snapshot(session_id)


def update_history(session_id: str, messages: Sequence[BaseMessage]) -> None:
    _CONVERSATIONS.update(session_id, messages)


def default_session_id() -> str:
    return get_current_session() or get_boot_session_id()


__all__ = ["ConversationStore", "get_history", "update_history", "default_session_id"]
