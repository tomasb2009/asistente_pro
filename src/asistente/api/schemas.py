from __future__ import annotations

from pydantic import BaseModel, Field


class QueryResponse(BaseModel):
    intent: str = Field(
        ...,
        description="Intención interna: weather | time | general_knowledge.",
    )
    reply: str
