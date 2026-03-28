"""
Respuesta en texto para comandos de hogar (formal, concisa).
"""

from __future__ import annotations

from asistente.config import get_settings
from asistente.home_zones import (
    parse_home_zone_slugs,
    slug_zone,
    user_wants_all_lights,
    validate_zone_before_publish,
)
from asistente.tools.mqtt_publish import (
    MqttNotConfiguredError,
    NoHomeZonesConfiguredError,
    publish_all_home_zones,
    publish_home_command,
)


def _action_es(action: str) -> str:
    return {"on": "encendido", "off": "apagado", "toggle": "alternado"}.get(action, action)


async def run_home_command(
    zone: str | None,
    action: str | None,
    *,
    user_message: str | None = None,
) -> str:
    import asyncio

    act = (action or "toggle").strip().lower()
    if act not in ("on", "off", "toggle"):
        act = "toggle"

    all_lights = user_wants_all_lights(user_message) or slug_zone(zone or "") == "todas"

    err = validate_zone_before_publish(zone, all_lights=all_lights)
    if err:
        return err

    try:
        if all_lights:
            await asyncio.to_thread(publish_all_home_zones, act)
        else:
            await asyncio.to_thread(publish_home_command, zone, act)
    except MqttNotConfiguredError:
        return (
            "Le ruego disculpe, señor; la domótica no está configurada en el servidor "
            "(falta MQTT_BROKER_HOST en el entorno)."
        )
    except NoHomeZonesConfiguredError:
        return (
            "Le ruego disculpe, señor; para todas las luces defina MQTT_HOME_ZONES "
            "en el servidor con la lista de zonas (coma)."
        )
    except OSError as e:
        return (
            f"Le ruego disculpe, señor; no pude contactar al broker MQTT ({e}). "
            "Compruebe la red y el Mosquitto en la Raspberry."
        )

    if all_lights:
        listed = ", ".join(parse_home_zone_slugs(get_settings().mqtt_home_zones))
        return (
            f"Orden cursada, señor: {_action_es(act)} las luces en todas las zonas "
            f"({listed})."
        )

    z = zone or "la zona indicada"
    return f"Orden cursada, señor: {_action_es(act)} lo correspondiente en {z}."
