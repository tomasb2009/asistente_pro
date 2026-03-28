"""Geocodificación gratuita vía Open-Meteo (sin API key)."""

from __future__ import annotations

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def resolve_city(name: str) -> tuple[float, float, str, str] | None:
    """
    Devuelve (lat, lon, nombre_display, timezone) o None si no hay resultados.
    """
    params = {"name": name.strip(), "count": 1, "language": "es", "format": "json"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(GEOCODING_URL, params=params)
        r.raise_for_status()
        data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    p = results[0]
    lat = float(p["latitude"])
    lon = float(p["longitude"])
    display = p.get("name", name)
    if admin := p.get("admin1"):
        if admin.strip().lower() != (display or "").strip().lower():
            display = f"{display}, {admin}"
    tz = p.get("timezone") or "UTC"
    return lat, lon, display, tz
