"""
Orquestación: texto → clasificación → herramienta o cadena de respuesta.
Memoria de sesión (un solo id interno); memoria larga vía RAG en conocimiento general.
"""

from __future__ import annotations

from asistente.handlers import answer_from_routed
from asistente.memory.ingest import try_ingest_from_message
from asistente.memory.session_store import DEFAULT_SESSION_ID, get_session_store
from asistente.router import RoutedQuery, route_user_message
from asistente.router_followup import refine_routed_with_history


async def run_pipeline(user_text: str) -> str:
    """CLI: misma memoria de sesión que la API."""
    _, reply = await run_pipeline_with_routing(user_text)
    return reply


async def run_pipeline_with_routing(user_text: str) -> tuple[RoutedQuery, str]:
    store = get_session_store()
    sid = DEFAULT_SESSION_ID
    hist = store.get_history_for_prompt(sid)
    last = store.get_last_routed(sid)

    routed = route_user_message(
        user_text,
        session_context=hist or None,
        last_routed=last,
    )
    routed = refine_routed_with_history(user_text, routed, last)
    reply = await answer_from_routed(routed, user_text, session_context=hist or None)

    store.append_turn(sid, user_text, reply, routed)
    try_ingest_from_message(user_text)

    return routed, reply
