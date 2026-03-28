from enum import StrEnum


class UserIntent(StrEnum):
    """Qué canal debe atender la petición (no confundir con 'tool' de LangChain)."""

    WEATHER = "weather"  # clima hoy o pronóstico
    TIME = "time"  # hora en una ciudad / zona
    GENERAL_KNOWLEDGE = "general_knowledge"  # cultura general → respuesta estilo Jarvis vía LLM
    HOME_COMMAND = "home_command"  # domótica vía MQTT (luces, enchufes, etc.)
