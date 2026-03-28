"""
Zonas domóticas configurables (MQTT_HOME_ZONES): normalización y validación.
"""

from __future__ import annotations

import re
import unicodedata

from asistente.config import Settings, get_settings


def slug_zone(name: str) -> str:
    """Clave MQTT: minúsculas, sin acentos, espacios y puntuación → underscore."""
    s = unicodedata.normalize("NFD", name.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "general"


def parse_home_zone_slugs(raw: str | None) -> list[str]:
    """Lista ordenada y sin duplicados a partir de MQTT_HOME_ZONES (coma)."""
    if not raw or not str(raw).strip():
        return []
    seen: set[str] = set()
    out: list[str] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        s = slug_zone(part)
        if not s:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def user_wants_all_lights(user_text: str | None) -> bool:
    """
    Encender/apagar todas las luces configuradas (no una sola habitación).
    """
    if not user_text or not str(user_text).strip():
        return False
    low = str(user_text).lower()
    if re.search(
        r"\b(todas|toda)\s+(las\s+)?(luces?|l[aá]mparas?)\b",
        low,
    ):
        return True
    if re.search(
        r"\b(enciende|prende|prender|apaga|apagar|activar|desactivar)\s+"
        r"tod(o|a)s\s+(las\s+)?(luces?|l[aá]mparas?)\b",
        low,
    ):
        return True
    if re.search(
        r"\b(luces?|l[aá]mparas?)\s+(de\s+)?(toda|todo)\s+(la\s+)?(casa|vivienda|hogar)\b",
        low,
    ):
        return True
    if re.search(
        r"\b(turn|switch)\s+(on|off)\s+all(\s+the)?\s+lights?\b",
        low,
    ):
        return True
    if re.search(
        r"\ball\s+lights?\s+(on|off)\b",
        low,
    ):
        return True
    if re.search(
        r"\b(enciende|prende|apaga)\s+tod(o|a)s\b",
        low,
    ) and re.search(r"\b(luz|luces|l[aá]mpara|l[aá]mparas|iluminaci[oó]n)\b", low):
        return True
    return False


def allowed_zone_slugs(settings: Settings | None = None) -> frozenset[str]:
    s = settings or get_settings()
    return frozenset(parse_home_zone_slugs(s.mqtt_home_zones))


def zones_block_for_router(settings: Settings | None = None) -> str:
    """Texto para el system prompt del router."""
    s = settings or get_settings()
    zones = parse_home_zone_slugs(s.mqtt_home_zones)
    if not zones:
        return (
            "Zonas domóticas: no hay lista cerrada en el servidor; el usuario puede "
            "nombrar cualquier habitación. Normalizá a minúsculas sin acentos "
            "(p. ej. salón → salon) en home_zone."
        )
    listed = ", ".join(zones)
    return (
        f"Zonas domóticas configuradas en el servidor (usá home_zone coherente con "
        f"una de ellas; aceptá sinónimos del usuario que mapeen al mismo espacio): "
        f"{listed}. "
        f"Si pide encender o apagar TODAS las luces, usá home_zone «todas» y la acción "
        f"on u off según corresponda; el servidor publicará en cada zona listada. "
        f"Si el usuario pide una habitación que no encaja con ninguna, igualmente "
        f"usá home_command y la mejor aproximación posible entre las listadas."
    )


def validate_zone_before_publish(
    zone: str | None,
    settings: Settings | None = None,
    *,
    all_lights: bool = False,
) -> str | None:
    """
    Si hay lista configurada, exige una zona reconocida.
    Devuelve mensaje de error para el usuario o None si OK.
    """
    s = settings or get_settings()
    allowed = allowed_zone_slugs(s)
    if all_lights:
        if not allowed:
            return (
                "Le ruego disculpe, señor; para actuar sobre todas las luces hace falta "
                "definir MQTT_HOME_ZONES en el servidor (lista de zonas separada por comas)."
            )
        return None
    if not allowed:
        return None
    z = slug_zone(zone or "")
    if not zone or not str(zone).strip():
        return (
            "Le ruego indique la habitación o zona, señor. "
            f"Las disponibles son: {', '.join(sorted(allowed))}."
        )
    if z not in allowed:
        return (
            f"Le ruego disculpe, señor; la zona «{zone.strip()}» no está entre las "
            f"configuradas. Puede usar: {', '.join(sorted(allowed))}. "
            "Añada la zona en MQTT_HOME_ZONES en el servidor si dispone de un módulo allí."
        )
    return None
