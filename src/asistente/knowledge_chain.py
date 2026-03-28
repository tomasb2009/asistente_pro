"""
Respuestas de conocimiento general: registro formal, sin nombre de personaje.
Memoria de sesión y RAG opcionales.
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from asistente.config import get_settings

_ASSISTANT_SYSTEM = (
    "Sos un asistente doméstico de confianza: tono serio, sobrio y cortés. "
    "Tratá al interlocutor de «señor» con naturalidad y mesura (no en cada oración). "
    "Hablá en español culto, claro y conciso; evitá coloquialismos y exclamaciones vacías. "
    "Sutil y educado; no menciones personajes de ficción ni digas cómo te llamás. "
    "Si piden otro idioma, respondé en ese idioma manteniendo el mismo registro. "
    "No inventes datos verificables; si no lo sabés, reconocelo brevemente y con tacto."
)


def _build_system_prompt(
    *,
    long_term_context: str | None,
    session_context: str | None,
) -> str:
    parts: list[str] = [_ASSISTANT_SYSTEM]
    if long_term_context:
        parts.append(
            "Datos guardados sobre el usuario (usá estos datos cuando la pregunta sea personal "
            "o cuando haga falta recordar gustos, nombre o preferencias):\n"
            f"{long_term_context}"
        )
    if session_context:
        parts.append(
            "Mensajes recientes de esta misma conversación (coherencia con el turno actual):\n"
            f"{session_context}"
        )
    return "\n\n".join(parts)


def answer_general_knowledge(
    user_message: str,
    *,
    session_context: str | None = None,
    long_term_context: str | None = None,
) -> str:
    settings = get_settings()
    system = _build_system_prompt(
        long_term_context=long_term_context,
        session_context=session_context,
    )
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=0.35,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "{message}"),
        ]
    )
    chain = prompt | llm
    out = chain.invoke({"message": user_message})
    return out.content if hasattr(out, "content") else str(out)
