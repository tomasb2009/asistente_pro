"""Hora y fecha local en una ciudad usando la timezone de Open-Meteo geocoding."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from asistente.tools.geocoding import resolve_city

_WEEKDAYS_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
_MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def _format_date_es(now: datetime) -> str:
    wd = _WEEKDAYS_ES[now.weekday()]
    m = _MONTHS_ES[now.month - 1]
    return f"{wd} {now.day} de {m} de {now.year}"


def _wants_calendar_date(user_message: str | None) -> bool:
    """Pregunta por fecha / día del calendario (no «un día soleado» del tiempo)."""
    if not user_message or not user_message.strip():
        return False
    low = user_message.lower()
    return bool(
        re.search(
            r"\b(qu[eé]\s+d[ií]a|qu[eé]\s+fecha|d[ií]a\s+es\s+hoy|fecha\s+de\s+hoy|"
            r"hoy\s+es\s+qu[eé]\s+d[ií]a|hoy\s+qu[eé]\s+d[ií]a|d[ií]a\s+de\s+la\s+semana|"
            r"qu[eé]\s+fecha\s+es|n[uú]mero\s+de\s+d[ií]a|calendario|"
            r"cu[aá]l\s+es\s+la\s+fecha|fecha\s+actual)\b",
            low,
        )
    )


def _wants_clock_time(user_message: str | None) -> bool:
    if not user_message or not user_message.strip():
        return True
    low = user_message.lower()
    return bool(
        re.search(
            r"\b(hora|horario|qu[eé]\s+hora|reloj)\b",
            low,
        )
    )


async def fetch_local_time_answer(
    city_query: str,
    user_message: str | None = None,
) -> str:
    resolved = await resolve_city(city_query)
    if resolved is None:
        return (
            f"Le ruego disculpe, señor; no pude localizar «{city_query}». "
            "¿Podría indicar otro nombre?"
        )

    _lat, _lon, display, tz_name = resolved
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)

    want_date = _wants_calendar_date(user_message)
    want_time = _wants_clock_time(user_message)

    if want_date and want_time:
        return (
            f"Si me permite, señor: en {display} hoy es {_format_date_es(now)}; "
            f"son las {now.strftime('%H:%M:%S')} (huso horario {tz_name})."
        )
    if want_date and not want_time:
        return (
            f"Si me permite, señor: en {display} hoy es {_format_date_es(now)} "
            f"(huso horario {tz_name})."
        )
    if want_time and not want_date:
        return (
            f"Si me permite, señor: en {display} son las {now.strftime('%H:%M:%S')} "
            f"(huso horario {tz_name})."
        )
    return (
        f"Si me permite, señor: en {display} hoy es {_format_date_es(now)}; "
        f"son las {now.strftime('%H:%M:%S')} (huso horario {tz_name})."
    )
