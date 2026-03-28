"""
Corrige la clasificación cuando el mensaje es un seguimiento (otro país, «¿y mañana?»).
"""

from __future__ import annotations

import re

from asistente.intents import UserIntent
from asistente.router import RoutedQuery


def _explicit_time(low: str) -> bool:
    """Hora en reloj o pregunta por fecha/día de calendario (no clima «hace un día…»)."""
    if re.search(
        r"\b(hora|horario|qu[eé]\s+hora|reloj)\b",
        low,
    ):
        return True
    return bool(
        re.search(
            r"\b(qu[eé]\s+d[ií]a|qu[eé]\s+fecha|d[ií]a\s+es\s+hoy|fecha\s+de\s+hoy|"
            r"hoy\s+qu[eé]\s+d[ií]a|d[ií]a\s+de\s+la\s+semana|calendario|"
            r"cu[aá]l\s+es\s+la\s+fecha|fecha\s+actual)\b",
            low,
        )
    )


def _explicit_weather(low: str) -> bool:
    return bool(
        re.search(
            r"\b(clima|lluvia|temperaturas?|pron[oó]stico|pronostico|qué tiempo|que tiempo|"
            r"viento|nublado|soleado|precipitacion|precipitación|temperatura|fr[ií]o|calor)\b",
            low,
        )
    )


def _explicit_home(low: str) -> bool:
    """Orden domótica explícita (no confundir con 'luz solar' sin verbo)."""
    return bool(
        re.search(
            r"\b(prende|prender|enciende|encender|apaga|apagar|activar|desactivar|"
            r"interruptor|enchufes?|dom[oó]tica)\b",
            low,
        )
        or re.search(
            r"\b(luz|luces)\b.{0,24}\b(prende|enciende|apaga|encender|apagar|pon|haz)\b",
            low,
        )
        or re.search(
            r"\b(prende|enciende|apaga|encender|apagar|pon|haz)\b.{0,32}\b(luz|luces)\b",
            low,
        )
    )


def _home_followup_from_gk(message: str) -> bool:
    """Seguimiento corto domótico mal clasificado como general_knowledge."""
    s = message.strip().lower()
    if len(s) > 90:
        return False
    if re.match(r"^\s*(¿)?\s*(y|también|tambien|además|ademas)\s+", s):
        return True
    return bool(
        re.search(
            r"\b(comedor|sal[oó]n|salon|cocina|dormitorio|baño|bano|habitaci[oó]n|"
            r"pasillo|terraza|garaje|entrada|luces?|luz|enchufe)\b",
            s,
        )
    )


def _followup_shape(message: str) -> bool:
    s = message.strip()
    if len(s) > 180:
        return False
    low = s.lower()
    if _explicit_time(low) or _explicit_weather(low) or _explicit_home(low):
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
    Ajusta seguimientos: mantiene hora/clima cuando el mensaje es corto y ambiguo,
    pero no pisa domótica ni un cambio claro hora↔clima ni órdenes de casa (prende/apaga…).
    """
    if last is None:
        return routed

    low = message.lower()

    if last.intent == UserIntent.HOME_COMMAND:
        if _explicit_time(low):
            return routed
        if _explicit_weather(low):
            return routed
        hz = routed.home_zone or routed.location or last.home_zone
        ha = routed.home_action or last.home_action
        if routed.intent == UserIntent.HOME_COMMAND:
            return RoutedQuery(
                intent=UserIntent.HOME_COMMAND,
                location=routed.location,
                forecast_days_ahead=0,
                home_zone=hz,
                home_action=ha,
            )
        if routed.intent == UserIntent.GENERAL_KNOWLEDGE and _home_followup_from_gk(message):
            return RoutedQuery(
                intent=UserIntent.HOME_COMMAND,
                location=last.location,
                forecast_days_ahead=0,
                home_zone=hz,
                home_action=ha,
            )

    if _explicit_time(low):
        return routed.model_copy(update={"intent": UserIntent.TIME})
    if _explicit_weather(low):
        return routed.model_copy(update={"intent": UserIntent.WEATHER})

    # Cambio de tema: no forzar el turno anterior (clima/hora) sobre domótica.
    if routed.intent == UserIntent.HOME_COMMAND:
        hz = routed.home_zone or routed.location or last.home_zone
        ha = routed.home_action or last.home_action
        return RoutedQuery(
            intent=UserIntent.HOME_COMMAND,
            location=routed.location,
            forecast_days_ahead=0,
            home_zone=hz,
            home_action=ha,
        )

    if _explicit_home(low) and last.intent in (
        UserIntent.TIME,
        UserIntent.WEATHER,
        UserIntent.GENERAL_KNOWLEDGE,
    ):
        hz = routed.home_zone or routed.location or last.home_zone
        ha = routed.home_action or last.home_action
        return RoutedQuery(
            intent=UserIntent.HOME_COMMAND,
            location=None,
            forecast_days_ahead=0,
            home_zone=hz,
            home_action=ha,
        )

    # Tras hora → clima o clima → hora: confiar en el modelo si ya cambió de intención.
    if last.intent == UserIntent.TIME and routed.intent == UserIntent.WEATHER:
        return routed
    if last.intent == UserIntent.WEATHER and routed.intent == UserIntent.TIME:
        return routed

    if routed.intent == UserIntent.GENERAL_KNOWLEDGE:
        return routed

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
