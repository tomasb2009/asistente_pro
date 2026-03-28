"""
Lógica de respuesta por intención; usada por el pipeline CLI y por la API.
"""

from __future__ import annotations

from asistente.config import get_settings
from asistente.intents import UserIntent
from asistente.knowledge_chain import answer_general_knowledge
from asistente.memory.long_term import retrieve_context
from asistente.router import RoutedQuery
from asistente.tools.home_reply import run_home_command
from asistente.tools.local_time import fetch_local_time_answer
from asistente.tools.weather import fetch_weather_answer


def _city_or_default(city: str | None) -> str:
    settings = get_settings()
    c = (city or "").strip()
    return c if c else settings.default_city


def _rag_query(message: str, session_context: str | None) -> str:
    """Mezcla mensaje actual + final del historial para recuperar hechos guardados."""
    parts = [message.strip()]
    if session_context:
        tail = session_context.strip()
        if len(tail) > 400:
            tail = tail[-400:]
        parts.append(tail)
    return "\n".join(parts)


async def answer_weather(city: str | None, forecast_days_ahead: int = 0) -> str:
    return await fetch_weather_answer(
        _city_or_default(city),
        days_ahead=forecast_days_ahead,
        user_message=None,
    )


async def answer_time(city: str | None, user_message: str | None = None) -> str:
    return await fetch_local_time_answer(_city_or_default(city), user_message=user_message)


def answer_knowledge(
    message: str,
    *,
    session_context: str | None = None,
) -> str:
    q = _rag_query(message, session_context)
    rag = retrieve_context(q)
    if not rag.strip():
        rag = retrieve_context(message)
    return answer_general_knowledge(
        message,
        session_context=session_context,
        long_term_context=rag if rag else None,
    )


async def answer_from_routed(
    routed: RoutedQuery,
    user_text: str,
    *,
    session_context: str | None = None,
) -> str:
    settings = get_settings()
    city = routed.location or settings.default_city

    if routed.intent == UserIntent.WEATHER:
        return await fetch_weather_answer(
            city,
            days_ahead=routed.forecast_days_ahead,
            user_message=user_text,
        )

    if routed.intent == UserIntent.TIME:
        return await fetch_local_time_answer(city, user_message=user_text)

    if routed.intent == UserIntent.HOME_COMMAND:
        return await run_home_command(
            routed.home_zone,
            routed.home_action,
            user_message=user_text,
        )

    return answer_knowledge(user_text, session_context=session_context)
