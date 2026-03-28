"""
Publicación MQTT para comandos de hogar (topic: {prefix}/{zona}, payload on|off|toggle).
"""

from __future__ import annotations

import paho.mqtt.client as mqtt

from asistente.config import get_settings
from asistente.home_zones import parse_home_zone_slugs, slug_zone


class MqttNotConfiguredError(RuntimeError):
    """Falta MQTT_BROKER_HOST en .env."""


class NoHomeZonesConfiguredError(RuntimeError):
    """MQTT_HOME_ZONES vacío: no hay zonas para «todas las luces»."""


def publish_all_home_zones(action: str | None) -> None:
    """Publica el mismo payload en cada topic `prefix/zona` de MQTT_HOME_ZONES."""
    settings = get_settings()
    if not settings.mqtt_broker_host:
        raise MqttNotConfiguredError("MQTT no configurado (MQTT_BROKER_HOST).")

    zones = parse_home_zone_slugs(settings.mqtt_home_zones)
    if not zones:
        raise NoHomeZonesConfiguredError("MQTT_HOME_ZONES vacío.")

    act = (action or "toggle").strip().lower()
    if act not in ("on", "off", "toggle"):
        act = "toggle"

    prefix = settings.mqtt_topic_prefix.strip("/")
    client = mqtt.Client(client_id=settings.mqtt_client_id)
    if settings.mqtt_username:
        client.username_pw_set(
            settings.mqtt_username,
            settings.mqtt_password or "",
        )

    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
    for z in zones:
        client.publish(f"{prefix}/{z}", act, qos=1, retain=False)
    client.disconnect()


def publish_home_command(zone: str | None, action: str | None) -> None:
    """
    Publica un comando en `MQTT_TOPIC_PREFIX/zona` con payload en minúsculas: on, off, toggle.
    """
    settings = get_settings()
    if not settings.mqtt_broker_host:
        raise MqttNotConfiguredError("MQTT no configurado (MQTT_BROKER_HOST).")

    z = slug_zone(zone or "general")
    act = (action or "toggle").strip().lower()
    if act not in ("on", "off", "toggle"):
        act = "toggle"

    topic = f"{settings.mqtt_topic_prefix.strip('/')}/{z}"

    client = mqtt.Client(client_id=settings.mqtt_client_id)
    if settings.mqtt_username:
        client.username_pw_set(
            settings.mqtt_username,
            settings.mqtt_password or "",
        )

    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=60)
    client.publish(topic, act, qos=1, retain=False)
    client.disconnect()
