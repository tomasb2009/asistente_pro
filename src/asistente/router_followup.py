"""
Corrige la clasificación cuando el mensaje es un seguimiento (otro país, «¿y mañana?»).
"""

from __future__ import annotations

import re

from asistente.intents import UserIntent
from asistente.router import RoutedQuery


def _explicit_time(low: str) -> bool:
    return bool(
        re.search(
            r"\b(hora|horario|qué hora|que hora|reloj)\b",
            low,
        )
    )


def _explicit_weather(low: str) -> bool:
    return bool(
        re.search(
            r"\b(clima|lluvia|temperaturas?|pron[oó]stico|pronostico|qué tiempo|que tiempo|"
            r"viento|nublado|soleado|precipitacion|precipitación)\b",
            low,
        )
    )


def _followup_shape(message: str) -> bool:
    s = message.strip()
    if len(s) > 180:
        return False
    low = s.lower()
    if _explicit_time(low) or _explicit_weather(low):
        return False
    if re.match(
        r"^\s*(¿)?\s*(y\s+)?(en|a|al|del|de\s+la|para)\s+",
        s,
        re.IGNORECASE,
    ):
        return True
    if len(s) < 60:
        return True
    if re.match(r"^\s*(¿)?\s*y\s+", s, re.IGNORECASE):
        return True
    return False


def refine_routed_with_history(
    message: str,
    routed: RoutedQuery,
    last: RoutedQuery | None,
) -> RoutedQuery:
    """
    Si el modelo cambió de intención en un seguimiento corto (p. ej. hora → clima),
    restaura la intención anterior salvo palabras claras de clima u hora.
    """
    if last is None:
        return routed
    if routed.intent == UserIntent.GENERAL_KNOWLEDGE:
        return routed

    low = message.lower()

    if _explicit_time(low):
        return routed.model_copy(update={"intent": UserIntent.TIME})
    if _explicit_weather(low):
        return routed.model_copy(update={"intent": UserIntent.WEATHER})

    if last.intent == UserIntent.GENERAL_KNOWLEDGE:
        return routed
    if routed.intent == last.intent:
        return routed
    if not _followup_shape(message):
        return routed

    loc = routed.location if routed.location else last.location
    if last.intent == UserIntent.TIME:
        return RoutedQuery(
            intent=UserIntent.TIME,
            location=loc,
            forecast_days_ahead=0,
        )
    if last.intent == UserIntent.WEATHER:
        return RoutedQuery(
            intent=UserIntent.WEATHER,
            location=loc,
            forecast_days_ahead=routed.forecast_days_ahead,
        )
    return routed
