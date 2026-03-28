"""
Clasificación de intención con el LLM (structured output).
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from asistente.config import Settings, get_settings
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


_ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Clasificá la petición del usuario en UNA intención:\n"
            "- weather: tiempo meteorológico (hoy o pronóstico futuro).\n"
            "- time: hora local en una ciudad o zona.\n"
            "- general_knowledge: cultura general, explicaciones, opiniones, "
            "cualquier cosa que NO sea obtener datos de clima u hora de APIs.\n"
            "Extraé `location` si menciona un lugar para clima/hora; si no dice ciudad, "
            "dejá location en null (el sistema usará la ciudad por defecto).\n"
            "Para pronóstico, poné forecast_days_ahead solo como ayuda; "
            "el servidor recalcula día (lunes, mañana…) y franja horaria "
            "(noche, tarde, entre las X y las Y).",
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


def route_user_message(message: str) -> RoutedQuery:
    settings = get_settings()
    llm = build_router_llm(settings)
    structured = llm.with_structured_output(RoutedQuery)
    chain = _ROUTER_PROMPT | structured
    return chain.invoke({"message": message})
