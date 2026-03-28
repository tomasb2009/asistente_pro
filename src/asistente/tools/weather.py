"""Clima con Open-Meteo: respuesta acotada a lo que el usuario preguntó."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean
from typing import Any

import httpx

from asistente.tools.geocoding import resolve_city
from asistente.tools.weather_codes import describe_sky_wmo
from asistente.tools.weather_day_parser import merge_forecast_days
from asistente.tools.weather_focus import WeatherAnswerFocus, classify_weather_focus
from asistente.tools.weather_time_window import (
    clip_window_to_now_if_today,
    collect_hourly_indices,
    parse_time_window,
    window_label_es,
)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_DAILY_FIELDS = (
    "weathercode,temperature_2m_max,temperature_2m_min,windspeed_10m_max,relative_humidity_2m_mean"
)

_HOURLY_FIELDS = (
    "temperature_2m,apparent_temperature,precipitation_probability,precipitation,"
    "cloudcover,weathercode,windspeed_10m,relative_humidity_2m,uv_index"
)

_WEEKDAY_ES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)


def _day_label(days_ahead: int) -> str:
    if days_ahead == 0:
        return "hoy"
    if days_ahead == 1:
        return "mañana"
    t = date.today() + timedelta(days=days_ahead)
    name = _WEEKDAY_ES[t.weekday()]
    return f"el {name} {t.day:02d}/{t.month:02d}"


def _safe_vals(hourly: dict[str, Any], key: str, indices: list[int]) -> list[float]:
    arr = hourly.get(key) or []
    out: list[float] = []
    for i in indices:
        if i < len(arr) and arr[i] is not None:
            try:
                out.append(float(arr[i]))
            except (TypeError, ValueError):
                pass
    return out


def _safe_ints(hourly: dict[str, Any], key: str, indices: list[int]) -> list[int]:
    arr = hourly.get(key) or []
    out: list[int] = []
    for i in indices:
        if i < len(arr) and arr[i] is not None:
            try:
                out.append(int(round(float(arr[i]))))
            except (TypeError, ValueError):
                pass
    return out


def _mode_int(vals: list[int]) -> int | None:
    if not vals:
        return None
    return max(set(vals), key=vals.count)


def _lluvia_riesgo_corto(p_max: float | None) -> str | None:
    if p_max is None:
        return None
    if p_max < 15:
        return "Riesgo bajo de precipitación según el modelo"
    if p_max < 40:
        return "Posibilidad acotada; conviene estar atento al radar local"
    if p_max < 65:
        return "Posibilidad moderada de precipitación"
    return "Alta probabilidad de precipitación en esa franja"


def _format_answer(
    focus: WeatherAnswerFocus,
    *,
    display: str,
    day_lbl: str,
    win_lbl: str,
    tw_full_day: bool,
    tmax_d: float | None,
    tmin_d: float | None,
    probs: list[float],
    apparent: list[float],
    temps_air: list[float],
    clouds: list[float],
    winds: list[float],
    hums: list[float],
    precs: list[float],
    wcodes: list[int],
    uvs: list[float],
) -> str:
    p_max = max(probs) if probs else None
    p_mean = mean(probs) if probs else None
    ca_min = min(apparent) if apparent else None
    ca_max = max(apparent) if apparent else None
    ca_mean = mean(apparent) if apparent else None
    ta_min = min(temps_air) if temps_air else None
    ta_max = max(temps_air) if temps_air else None
    ta_mean = mean(temps_air) if temps_air else None
    c_mean = mean(clouds) if clouds else None
    w_max = max(winds) if winds else None
    h_mean = mean(hums) if hums else None
    prec_sum = sum(precs) if precs else None
    wcode_rep = _mode_int(wcodes) if wcodes else None
    sky = describe_sky_wmo(wcode_rep)
    uv_max = max(uvs) if uvs else None

    head = f"Si me permite, señor: en {display}, {day_lbl}, {win_lbl}"
    bits: list[str] = [head]

    g = focus.general

    show_rain_p = g or focus.rain_probability or focus.rain_accumulation
    show_rain_mm = focus.rain_accumulation or (g and prec_sum is not None and prec_sum > 0.01)
    show_sens = g or focus.sensation
    show_air = g or focus.air_temperature
    show_wind = g or focus.wind
    show_clouds = g or focus.clouds
    show_hum = g or focus.humidity
    show_sky = g or focus.sky_condition
    show_uv = focus.uv or (g and uv_max is not None and uv_max >= 1.0)

    # Panorama diario solo si preguntan de forma amplia y el tramo es el día entero
    if g and tw_full_day and tmax_d is not None and tmin_d is not None:
        bits.append(
            f"temperatura prevista para el día: máxima {tmax_d:.0f} °C, mínima {tmin_d:.0f} °C"
        )

    if show_rain_p and p_max is not None:
        extra = f", media en la franja {p_mean:.0f} %" if p_mean is not None else ""
        bits.append(f"probabilidad de precipitación hasta un {p_max:.0f} %{extra}")
        if g and p_max is not None:
            hint = _lluvia_riesgo_corto(p_max)
            if hint:
                bits.append(hint)

    if show_rain_mm and prec_sum is not None and prec_sum > 0.01:
        bits.append(f"lluvia acumulada en el tramo: unos {prec_sum:.1f} mm")

    if show_sens:
        if ca_min is not None and ca_max is not None:
            extra = f" (media {ca_mean:.0f} °C)" if ca_mean is not None else ""
            bits.append(f"sensación térmica entre {ca_min:.0f} °C y {ca_max:.0f} °C{extra}")
        elif ca_mean is not None:
            bits.append(f"sensación térmica media {ca_mean:.0f} °C")

    if show_air and (ta_min is not None or ta_max is not None):
        if ta_min is not None and ta_max is not None:
            extra = f" (media {ta_mean:.0f} °C)" if ta_mean is not None else ""
            bits.append(f"temperatura del aire entre {ta_min:.0f} °C y {ta_max:.0f} °C{extra}")
        elif ta_mean is not None:
            bits.append(f"temperatura del aire en torno a {ta_mean:.0f} °C")

    if show_clouds and c_mean is not None:
        bits.append(f"nubosidad media {c_mean:.0f} %")

    if show_hum and h_mean is not None:
        bits.append(f"humedad relativa media {h_mean:.0f} %")

    if show_wind and w_max is not None:
        bits.append(f"viento hasta {w_max:.0f} km/h en esa franja")

    if show_sky:
        bits.append(f"cielo: {sky}")

    if show_uv and uv_max is not None:
        bits.append(f"índice UV máximo en la franja: {uv_max:.1f}")

    return "; ".join(bits) + "."


async def fetch_weather_answer(
    city_query: str,
    *,
    days_ahead: int = 0,
    user_message: str | None = None,
) -> str:
    msg = user_message or ""
    focus = classify_weather_focus(msg)
    merged = merge_forecast_days(msg, days_ahead)
    tw = parse_time_window(msg)
    merged = min(max(merged, 0), 7)

    resolved = await resolve_city(city_query)
    if resolved is None:
        return (
            f"Le ruego disculpe, señor; no pude localizar «{city_query}». "
            "¿Podría indicar otro nombre o región?"
        )

    lat, lon, display, tz = resolved
    target = date.today() + timedelta(days=merged)
    forecast_days = min(max(merged + 2, 7), 16)

    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "forecast_days": forecast_days,
        "daily": _DAILY_FIELDS,
        "hourly": _HOURLY_FIELDS,
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(FORECAST_URL, params=params)
        r.raise_for_status()
        data = r.json()

    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    if merged >= len(dates):
        return f"Le pido disculpas, señor; no dispongo del pronóstico para {target} en {display}."

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return f"Le pido disculpas, señor; no recibí datos horarios para {display}."

    tw_use = tw
    if merged == 0:
        tw_use = clip_window_to_now_if_today(tw, target_date=target, tz_name=tz)

    indices = collect_hourly_indices(times, target, tw_use)
    if not indices:
        return (
            f"Le ruego disculpe, señor; no dispongo de datos para {display}, {_day_label(merged)}, "
            f"en «{window_label_es(tw_use)}». "
            "Si la franja ya pasó, pruebe con otra hora o con el día siguiente."
        )

    probs = _safe_vals(hourly, "precipitation_probability", indices)
    apparent = _safe_vals(hourly, "apparent_temperature", indices)
    temps_air = _safe_vals(hourly, "temperature_2m", indices)
    clouds = _safe_vals(hourly, "cloudcover", indices)
    winds = _safe_vals(hourly, "windspeed_10m", indices)
    hums = _safe_vals(hourly, "relative_humidity_2m", indices)
    precs = _safe_vals(hourly, "precipitation", indices)
    wcodes = _safe_ints(hourly, "weathercode", indices)
    uvs = _safe_vals(hourly, "uv_index", indices)

    idx_d = merged
    tmax_d = (daily.get("temperature_2m_max") or [None])[idx_d]
    tmin_d = (daily.get("temperature_2m_min") or [None])[idx_d]

    return _format_answer(
        focus,
        display=display,
        day_lbl=_day_label(merged),
        win_lbl=window_label_es(tw_use),
        tw_full_day=tw_use.is_full_day,
        tmax_d=float(tmax_d) if tmax_d is not None else None,
        tmin_d=float(tmin_d) if tmin_d is not None else None,
        probs=probs,
        apparent=apparent,
        temps_air=temps_air,
        clouds=clouds,
        winds=winds,
        hums=hums,
        precs=precs,
        wcodes=wcodes,
        uvs=uvs,
    )
