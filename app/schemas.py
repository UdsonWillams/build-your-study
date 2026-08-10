"""Modelos Pydantic usados na API."""

from pydantic import BaseModel, Field


class ProgressIn(BaseModel):
    topic_id: int
    # Nota de 0 a 10 do tópico. Nula em tópicos sem exercícios.
    score: float | None = Field(default=None, ge=0, le=10)


class ProgressOut(BaseModel):
    completed_topic_ids: list[int]
    # Melhor nota já obtida, por id de tópico.
    scores: dict[int, float] = {}
