"""Infraestrutura de componentes com pontos de variação.

Cada ponto de variação é uma **interface abstrata** (Strategy). Cada variante é
um **componente** concreto registrado com o *id da feature* do modelo. Em tempo
de inicialização, o microservice pede ao registro a variante resolvida na
configuração do produto — o cliente fica acoplado só à abstração, como o
``NETCDFLoader`` → ``NETCDFParser`` do WISE.
"""
from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class VariationPoint(Generic[T]):
    def __init__(self, binding: str, interface: type):
        self.binding = binding
        self.interface = interface
        self._variants: dict[str, type] = {}

    def variant(self, feature_id: str):
        """Decorador: registra uma classe como variante do ponto de variação."""
        def deco(cls):
            if not issubclass(cls, self.interface):
                raise TypeError(f"{cls.__name__} não implementa {self.interface.__name__}")
            cls.feature_id = feature_id
            self._variants[feature_id] = cls
            return cls
        return deco

    def create(self, feature_id: str, **kwargs) -> T:
        try:
            return self._variants[feature_id](**kwargs)
        except KeyError:
            raise ValueError(f"Variante '{feature_id}' não existe em '{self.binding}'. "
                             f"Disponíveis: {list(self._variants)}") from None

    def create_many(self, feature_ids: list[str], **kwargs) -> list[T]:
        return [self.create(f, **kwargs) for f in feature_ids]

    @property
    def variants(self) -> list[str]:
        return list(self._variants)
