"""
Orquestación: texto → clasificación → herramienta o cadena Jarvis.
"""

from __future__ import annotations

from asistente.handlers import answer_from_routed
from asistente.router import RoutedQuery, route_user_message


async def run_pipeline(user_text: str) -> str:
    routed = route_user_message(user_text)
    return await answer_from_routed(routed, user_text)


async def run_pipeline_with_routing(user_text: str) -> tuple[RoutedQuery, str]:
    """Igual que `run_pipeline`, pero devuelve la clasificación para la API."""
    routed = route_user_message(user_text)
    reply = await answer_from_routed(routed, user_text)
    return routed, reply
