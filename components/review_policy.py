"""Ponto de variação **Política de Revisão** (xor): SimplesCego | DuploCego | Aberta.

A política decide o que cada papel enxerga: o revisor vê os autores? O autor vê
o nome do revisor?
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .base import VariationPoint


class ReviewPolicy(ABC):
    label = "?"
    reviewer_sees_authors: bool
    author_sees_reviewer: bool

    def submission_for_reviewer(self, sub: dict) -> dict:
        if self.reviewer_sees_authors:
            return sub
        return {**sub, "authors": "[anônimo]", "author_id": None}

    def review_for_author(self, review: dict) -> dict:
        if self.author_sees_reviewer:
            return review
        return {**review, "reviewer_id": None, "reviewer_name": "Revisor anônimo"}

    @abstractmethod
    def describe(self) -> str: ...


review_vp: VariationPoint[ReviewPolicy] = VariationPoint("review_policy", ReviewPolicy)


@review_vp.variant("SimplesCego")
class SingleBlind(ReviewPolicy):
    label = "Simples-cego"
    reviewer_sees_authors = True
    author_sees_reviewer = False

    def describe(self):
        return "O revisor conhece os autores; os autores não conhecem o revisor."


@review_vp.variant("DuploCego")
class DoubleBlind(ReviewPolicy):
    label = "Duplo-cego"
    reviewer_sees_authors = False
    author_sees_reviewer = False

    def describe(self):
        return "Autores e revisores permanecem anônimos entre si."


@review_vp.variant("Aberta")
class OpenReview(ReviewPolicy):
    label = "Revisão aberta"
    reviewer_sees_authors = True
    author_sees_reviewer = True

    def describe(self):
        return "Identidades de autores e revisores são públicas."
