"""Hora local en una ciudad usando la timezone de Open-Meteo geocoding."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from asistente.tools.geocoding import resolve_city


async def fetch_local_time_answer(city_query: str) -> str:
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
    return (
        f"Si me permite, señor: en {display} son las {now.strftime('%H:%M:%S')} "
        f"(huso horario {tz_name})."
    )
