"""
Clasificación de intención con el LLM (structured output).
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from asistente.config import Settings, get_settings
from asistente.home_zones import zones_block_for_router
from asistente.intents import UserIntent


class RoutedQuery(BaseModel):
    intent: UserIntent = Field(description="Tipo de petición del usuario.")
    location: str | None = Field(
        default=None,
        description="Ciudad o lugar para clima/hora, si aplica; null si no se menciona.",
    )
    forecast_days_ahead: int = Field(
        default=0,
        ge=0,
        le=7,
        description="Para clima: 0=hoy/ahora, 1=mañana, etc.",
    )
    home_zone: str | None = Field(
        default=None,
        description="Zona de la casa para domótica: comedor, dormitorio, cocina, salon… "
        "Si pide todas las luces, poné «todas». No uses este campo para ciudades de clima/hora.",
    )
    home_action: str | None = Field(
        default=None,
        description="Para domótica: on, off o toggle según encender, apagar o alternar.",
    )


def _last_block(last: RoutedQuery | None) -> str:
    if last is None:
        return ""
    loc = last.location or "(no indicó lugar antes)"
    hz = last.home_zone or "(no indicó zona antes)"
    ha = last.home_action or "(igual acción que antes)"
    if last.intent == UserIntent.HOME_COMMAND:
        return (
            f"Continuidad: la petición anterior fue «{UserIntent.HOME_COMMAND.value}» "
            f"(zona previa: {hz}, acción: {ha}). "
            "Si el usuario solo cambia de habitación («¿y en el salón?») o repite orden, "
            "mantené intención home_command y actualizá home_zone/home_action."
        )
    return (
        f"Continuidad: la petición anterior fue «{last.intent.value}» "
        f"(lugar previo: {loc}). "
        "Si el usuario solo cambia de ciudad/país o dice «¿y mañana?», «¿y allí?», "
        "mantené el MISMO tipo (hora o clima) salvo que pida explícitamente la otra cosa."
    )


_ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Clasificá la petición del usuario en UNA intención:\n"
            "- weather: tiempo meteorológico (hoy o pronóstico futuro).\n"
            "- time: hora local, fecha de hoy, día de la semana o calendario en una ciudad; "
            "«¿qué día es hoy?», «¿qué fecha es?» van aquí, NO a conocimiento general.\n"
            "- home_command: órdenes para la casa (luces, enchufes, interruptores) "
            "mediante MQTT; el usuario nombra habitación o zona (comedor, cocina, salón…).\n"
            "- general_knowledge: cultura general, explicaciones, opiniones, "
            "cualquier cosa que NO sea clima, hora ni domótica.\n"
            "Extraé `location` solo para clima/hora (ciudad o lugar geográfico); "
            "para la casa usá `home_zone` (comedor, dormitorio…), nunca mezcles ciudad "
            "con habitación.\n"
            "Para home_command rellená `home_action`: on (encender), off (apagar), "
            "toggle (alternar o si no queda claro).\n"
            "Para pronóstico, poné forecast_days_ahead solo como ayuda; "
            "el servidor recalcula día (lunes, mañana…) y franja horaria "
            "(noche, tarde, entre las X y las Y).\n"
            "{home_zones}\n"
            "{continuity}",
        ),
        ("human", "{message}"),
    ]
)


def build_router_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=0,
    )


def route_user_message(
    message: str,
    session_context: str | None = None,
    last_routed: RoutedQuery | None = None,
) -> RoutedQuery:
    settings = get_settings()
    llm = build_router_llm(settings)
    structured = llm.with_structured_output(RoutedQuery)
    chain = _ROUTER_PROMPT | structured
    text = message
    if session_context:
        text = (
            "Historial reciente de esta conversación:\n"
            f"{session_context}\n\n---\nPetición actual del usuario:\n{message}"
        )
    return chain.invoke(
        {
            "message": text,
            "home_zones": zones_block_for_router(settings),
            "continuity": _last_block(last_routed),
        }
    )
