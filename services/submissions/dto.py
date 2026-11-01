"""DTO — objetos de transferência do Submissions Service."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SubmissionIn(BaseModel):
    author_id: int
    title: str = Field(min_length=5)
    abstract: str = ""
    authors: str = Field(description="Nomes separados por vírgula")
    keywords: str = Field(default="", description="Termos separados por vírgula")
    format: str = Field(description="ArtigoCompleto | ResumoExpandido | Poster (conforme produto)")


class SubmissionOut(BaseModel):
    id: int
    author_id: int
    title: str
    abstract: str
    authors: str
    keywords: str
    format: str
    status: str
    created_at: str


class StatusIn(BaseModel):
    status: str = Field(pattern="^(submitted|under_review|accepted|rejected)$")


class FormatOut(BaseModel):
    id: str
    label: str
