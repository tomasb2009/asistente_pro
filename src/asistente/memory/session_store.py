"""
Memoria de sesión en proceso: un solo dispositivo → id interno fijo.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from asistente.intents import UserIntent
from asistente.router import RoutedQuery

# Un solo hilo conversacional por instancia del servidor (sin id en la API).
DEFAULT_SESSION_ID = "default"


@dataclass
class _SessionData:
    turns: deque[tuple[str, str]] = field(default_factory=lambda: deque())
    last_seen: float = field(default_factory=time.time)
    last_routed: dict[str, str | int | None] | None = None


class SessionStore:
    def __init__(self, *, ttl_seconds: int, max_turn_pairs: int) -> None:
        self._ttl = ttl_seconds
        self._max_pairs = max_turn_pairs
        self._lock = threading.Lock()
        self._sessions: dict[str, _SessionData] = {}

    def _purge_unlocked(self) -> None:
        now = time.time()
        dead = [sid for sid, d in self._sessions.items() if now - d.last_seen > self._ttl]
        for sid in dead:
            del self._sessions[sid]

    def get_history_for_prompt(self, session_id: str) -> str:
        """Turnos previos (sin el mensaje actual), para router y LLM."""
        with self._lock:
            self._purge_unlocked()
            data = self._sessions.get(session_id)
            if not data or not data.turns:
                return ""
            lines: list[str] = []
            for u, a in data.turns:
                lines.append(f"Usuario: {u}")
                lines.append(f"Asistente: {a}")
            return "\n".join(lines)

    def get_last_routed(self, session_id: str) -> RoutedQuery | None:
        with self._lock:
            self._purge_unlocked()
            data = self._sessions.get(session_id)
            if not data or not data.last_routed:
                return None
            d = data.last_routed
            return RoutedQuery(
                intent=UserIntent(d["intent"]),
                location=d.get("location"),
                forecast_days_ahead=int(d.get("forecast_days_ahead") or 0),
                home_zone=d.get("home_zone"),
                home_action=d.get("home_action"),
            )

    def append_turn(
        self,
        session_id: str,
        user: str,
        assistant: str,
        routed: RoutedQuery,
    ) -> None:
        with self._lock:
            self._purge_unlocked()
            if session_id not in self._sessions:
                self._sessions[session_id] = _SessionData()
            d = self._sessions[session_id]
            d.last_seen = time.time()
            d.turns.append((user, assistant))
            while len(d.turns) > self._max_pairs:
                d.turns.popleft()
            d.last_routed = {
                "intent": routed.intent.value,
                "location": routed.location,
                "forecast_days_ahead": routed.forecast_days_ahead,
                "home_zone": routed.home_zone,
                "home_action": routed.home_action,
            }


_SESSION: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _SESSION
    if _SESSION is None:
        from asistente.config import get_settings

        s = get_settings()
        _SESSION = SessionStore(
            ttl_seconds=s.session_ttl_seconds,
            max_turn_pairs=s.session_max_turn_pairs,
        )
    return _SESSION
