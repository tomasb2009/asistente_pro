"""
Entrada común: GET con el mensaje; memoria de sesión única en el servidor.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from asistente.api.schemas import QueryResponse
from asistente.pipeline import run_pipeline_with_routing

router = APIRouter(tags=["query"])


@router.get("/query", response_model=QueryResponse)
async def get_query(
    message: str = Query(
        ...,
        min_length=1,
        description="Petición del usuario (texto o transcripción de voz).",
    ),
) -> QueryResponse:
    routed, reply = await run_pipeline_with_routing(message)
    return QueryResponse(intent=routed.intent.value, reply=reply)
