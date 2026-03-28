"""
Franjas horarias en lenguaje natural (español) para pronóstico por hora.

Prioridad: rangos explícitos > momentos del día (madrugada, tarde, noche…).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


@dataclass(frozen=True)
class TimeWindow:
    """Ventana en hora civil local. Si start_h > end_h, cruza medianoche (día+1)."""

    start_h: int
    end_h: int  # inclusive; si overnight, end_h es del día siguiente

    @property
    def is_overnight(self) -> bool:
        return self.start_h > self.end_h

    @property
    def is_full_day(self) -> bool:
        return self.start_h == 0 and self.end_h == 23 and not self.is_overnight


def _clamp_h(h: int) -> int:
    return max(0, min(23, h))


def parse_time_window(message: str) -> TimeWindow:
    """
    Devuelve la franja pedida; por defecto día completo (0–23).
    """
    if not (msg := message.strip()):
        return TimeWindow(0, 23)

    low = msg.lower()
    folded = _fold(msg)

    # 1) entre las X y las Y (o entre X y Y)
    m = re.search(
        r"\bentre\s+las?\s+(\d{1,2})\s+y\s+(?:las?\s+)?(\d{1,2})\b",
        low,
    ) or re.search(
        r"\bde\s+las?\s+(\d{1,2})\s+a\s+(?:las?\s+)?(\d{1,2})\s*(?:horas?)?\b",
        low,
    )
    if m:
        a, b = _clamp_h(int(m.group(1))), _clamp_h(int(m.group(2)))
        if a > b:
            return TimeWindow(a, b)  # overnight
        return TimeWindow(min(a, b), max(a, b))

    m = re.search(r"\bde\s+(\d{1,2})\s+a\s+(\d{1,2})\b", low)
    if m:
        a, b = _clamp_h(int(m.group(1))), _clamp_h(int(m.group(2)))
        if a > b:
            return TimeWindow(a, b)
        return TimeWindow(min(a, b), max(a, b))

    # 2) a las X (una hora; usamos ventana de 1 h)
    m = re.search(r"\ba\s+las\s+(\d{1,2})(?:\s*h|\s*horas?)?\b", low)
    if m:
        h = _clamp_h(int(m.group(1)))
        return TimeWindow(h, h)

    # 3) Momentos del día (orden: más específicos primero)
    if re.search(
        r"\b(?:por\s+la\s+)?madrugada\b|\b(?:la\s+)?madrugada\b",
        folded,
    ):
        return TimeWindow(0, 5)

    if (
        "por la mañana" in low
        or "por la manana" in folded
        or re.search(r"\ba\s+la\s+mañana\b", low)
        or re.search(r"\besta\s+mañana\b", low)
    ):
        return TimeWindow(6, 11)

    if re.search(r"\bmediod[ií]a\b|\bal\s+mediod[ií]a\b", low):
        return TimeWindow(12, 15)

    # Evitar «más tarde» (luego) confundido con la tarde del día
    low_sin_mas_tarde = re.sub(r"más\s+tarde|mas\s+tarde", " ", low, flags=re.IGNORECASE)
    if re.search(r"\b(?:por\s+la\s+|esta\s+)tarde\b|\bla\s+tarde\b", low_sin_mas_tarde):
        return TimeWindow(16, 20)

    if re.search(
        r"\b(?:por\s+la\s+)?noche\b|\besta\s+noche\b",
        low,
    ) or re.search(r"\bnoche\b", folded):
        return TimeWindow(21, 23)

    return TimeWindow(0, 23)


def window_label_es(tw: TimeWindow) -> str:
    if tw.is_full_day:
        return "a lo largo del día"
    if tw.is_overnight:
        return f"desde las {tw.start_h:02d}:00 hasta las {tw.end_h:02d}:00 del día siguiente"
    if tw.start_h == tw.end_h:
        return f"alrededor de las {tw.start_h:02d}:00"
    return f"entre las {tw.start_h:02d}:00 y las {tw.end_h:02d}:00"


def clip_window_to_now_if_today(
    tw: TimeWindow,
    *,
    target_date: date,
    tz_name: str,
) -> TimeWindow:
    """Si hoy es el día pedido, no incluir horas ya pasadas (mejor uso de 'esta noche')."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    if now.date() != target_date or tw.is_full_day:
        return tw
    if tw.is_overnight:
        return tw
    cur = now.hour
    if tw.end_h < cur:
        return tw  # franja ya pasada; el formateador puede advertir
    start = max(tw.start_h, cur)
    if start > tw.end_h:
        return tw
    return TimeWindow(start, tw.end_h)


def collect_hourly_indices(
    times: list[str],
    target_date: date,
    tw: TimeWindow,
) -> list[int]:
    """
    Índices en arrays de Open-Meteo que caen en la ventana (fecha local del API).
    """
    out: list[int] = []
    day_next = target_date + timedelta(days=1)

    for i, ts in enumerate(times):
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        d = dt.date()
        h = dt.hour
        if not tw.is_overnight:
            if d != target_date:
                continue
            if tw.is_full_day:
                out.append(i)
                continue
            if tw.start_h <= h <= tw.end_h:
                out.append(i)
        else:
            if d == target_date and h >= tw.start_h:
                out.append(i)
            elif d == day_next and h <= tw.end_h:
                out.append(i)

    return out
