"""Códigos WMO de Open-Meteo → descripción breve en español."""

from __future__ import annotations


def describe_sky_wmo(code: int | None) -> str:
    if code is None:
        return "estado del cielo no disponible"
    c = int(code)
    if c == 0:
        return "cielo despejado"
    if c in (1,):
        return "principalmente despejado"
    if c == 2:
        return "parcialmente nublado"
    if c == 3:
        return "nublado"
    if c in (45, 48):
        return "niebla"
    if 51 <= c <= 55:
        return "llovizna"
    if 56 <= c <= 57:
        return "llovizna helada"
    if 61 <= c <= 63:
        return "lluvia"
    if c in (65, 66, 67):
        return "lluvia fuerte o helada"
    if 71 <= c <= 73:
        return "nieve"
    if c in (75, 77):
        return "nieve fuerte o granos"
    if 80 <= c <= 82:
        return "chubascos"
    if c in (85, 86):
        return "chubascos de nieve"
    if c == 95:
        return "tormenta"
    if c in (96, 98, 99):
        return "tormenta con granizo"
    return f"condición meteorológica (código {c})"
