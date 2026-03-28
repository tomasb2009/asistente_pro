"""
Lógica de respuesta por intención; usada por el pipeline CLI y por la API.
"""

from __future__ import annotations

from asistente.config import get_settings
from asistente.intents import UserIntent
from asistente.knowledge_chain import answer_general_knowledge
from asistente.router import RoutedQuery
from asistente.tools.local_time import fetch_local_time_answer
from asistente.tools.weather import fetch_weather_answer


def _city_or_default(city: str | None) -> str:
    settings = get_settings()
    c = (city or "").strip()
    return c if c else settings.default_city


async def answer_weather(city: str | None, forecast_days_ahead: int = 0) -> str:
    return await fetch_weather_answer(
        _city_or_default(city),
        days_ahead=forecast_days_ahead,
        user_message=None,
    )


async def answer_time(city: str | None) -> str:
    return await fetch_local_time_answer(_city_or_default(city))


def answer_knowledge(message: str) -> str:
    return answer_general_knowledge(message)


async def answer_from_routed(routed: RoutedQuery, user_text: str) -> str:
    settings = get_settings()
    city = routed.location or settings.default_city

    if routed.intent == UserIntent.WEATHER:
        return await fetch_weather_answer(
            city,
            days_ahead=routed.forecast_days_ahead,
            user_message=user_text,
        )

    if routed.intent == UserIntent.TIME:
        return await fetch_local_time_answer(city)

    return answer_general_knowledge(user_text)
