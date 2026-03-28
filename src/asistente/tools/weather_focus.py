"""
Qué aspectos del tiempo interesan según la redacción de la pregunta (español).

Si hay señales concretas, no se rellena con datos no solicitados (p. ej. solo lluvia).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


@dataclass(frozen=True)
class WeatherAnswerFocus:
    """Qué incluir en la respuesta. `general` implica panorama razonable (sin forzar UV)."""

    general: bool = False
    rain_probability: bool = False
    rain_accumulation: bool = False
    sensation: bool = False
    air_temperature: bool = False
    wind: bool = False
    clouds: bool = False
    humidity: bool = False
    sky_condition: bool = False
    uv: bool = False


def classify_weather_focus(message: str) -> WeatherAnswerFocus:
    if not (raw := message.strip()):
        return WeatherAnswerFocus(general=True)

    f = _fold(raw)

    # --- Señales específicas (orden no crítico; se combinan) ---
    rain_prob = bool(
        re.search(
            r"probabilidad|llovera|lloverá|\bllover\b|lloviendo|lluvia|paraguas|"
            r"precipitacion|chaparron|chubasco|llovizna|gotear|gotas|diluviar|"
            r"pronostico\s+de\s+lluvia|prevision\s+de\s+lluvia|"
            r"habra\s+lluvia|\bhay\s+pronostico",
            f,
        )
    )
    rain_mm = bool(
        re.search(
            r"\bmm\b|milimetros?|litros?\s+de\s+agua|cuanto\s+caera|cuanta\s+lluvia|"
            r"acumulad|cantidad\s+de\s+lluvia",
            f,
        )
    )

    sensation = bool(
        re.search(r"sensacion\s+termica", f)
        or re.search(
            r"\bcalor\b|\bfrio\b|\bfrescor\b|bochorno|acalorado|helada\b|sofocante",
            f,
        )
    )

    air_temp = bool(re.search(r"\btemperatura\b", f)) or bool(
        re.search(r"\bgrados\b|celsius|°c|centigrados", f)
    )

    wind = bool(re.search(r"viento|rafaga|ventoso|soplar|huracan|temporal\b", f))
    clouds = bool(re.search(r"nubosidad|nublado|nubes\b|cubierto\b", f))
    humidity = bool(re.search(r"humedad|humedo", f))
    sky = bool(
        re.search(
            r"estado\s+del\s+cielo|\bcielo\b|despejado|soleado|sol\b(?!amente)|"
            r"anochecer\s+con",
            f,
        )
    )
    uv = bool(re.search(r"\buv\b|ultravioleta|indice\s+uv|radiacion\s+solar", f))

    specific_any = any(
        (
            rain_prob,
            rain_mm,
            sensation,
            air_temp,
            wind,
            clouds,
            humidity,
            sky,
            uv,
        )
    )

    if not specific_any:
        return WeatherAnswerFocus(general=True)

    # «Pronóstico», «qué tiempo…» u otras genéricas no deben anular un matiz concreto
    # (p. ej. «¿hay pronóstico de lluvia a la noche?» → solo lluvia).

    return WeatherAnswerFocus(
        general=False,
        rain_probability=rain_prob,
        rain_accumulation=rain_mm,
        sensation=sensation,
        air_temperature=air_temp,
        wind=wind,
        clouds=clouds,
        humidity=humidity,
        sky_condition=sky,
        uv=uv,
    )
