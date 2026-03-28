"""
Resuelve «mañana», «el lunes», etc. a días desde hoy (zona local del servidor).

Si el texto nombra un día, este cálculo prevalece sobre el valor del clasificador LLM.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date


def _fold_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


# Python: lunes=0 … domingo=6
_WEEKDAY_ALIASES: dict[str, int] = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}


def _days_until_weekday(today: date, target_weekday: int) -> int:
    return (target_weekday - today.weekday()) % 7


def _strip_morning_uses_of_manana(low: str) -> str:
    """«Mañana» como momento del día (no como «el día siguiente»)."""
    s = low
    s = re.sub(r"\b(por|a|de|durante|en)\s+la\s+mañana\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\besta\s+mañana\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\besta\s+manana\b", " ", s, flags=re.IGNORECASE)
    return s


def parse_days_ahead_from_spanish(message: str) -> int | None:
    """
    Si el texto indica un día concreto, devuelve días desde hoy (0 = hoy).
    Si no hay indicación clara, devuelve None (usar fallback del LLM).
    """
    raw = message.strip()
    low = raw.lower()
    folded = _fold_accents(raw)

    if "pasado mañana" in low or "pasado manana" in folded:
        return 2

    low_for_tomorrow = _strip_morning_uses_of_manana(low)
    folded_tom = _fold_accents(low_for_tomorrow)

    # «mañana» = día siguiente (ya excluido «pasado mañana» arriba)
    if re.search(r"\bmañana\b", low_for_tomorrow) or re.search(r"\bmanana\b", folded_tom):
        return 1

    if re.search(r"\bhoy\b", low):
        return 0

    # Días de la semana (nombre más largo primero)
    for name in sorted(_WEEKDAY_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", folded):
            target = _WEEKDAY_ALIASES[name]
            return _days_until_weekday(date.today(), target)

    return None


def merge_forecast_days(message: str, llm_days: int) -> int:
    parsed = parse_days_ahead_from_spanish(message)
    if parsed is not None:
        return min(max(parsed, 0), 7)
    return min(max(llm_days, 0), 7)
