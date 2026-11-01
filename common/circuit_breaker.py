"""Circuit Breaker (Nygard, *Release It!*) — usado no WISE-Parser e aqui.

Após ``threshold`` falhas consecutivas o circuito ABRE e as chamadas ao serviço
remoto são bloqueadas por ``reset_timeout`` segundos (falha rápida). Depois disso
entra em HALF-OPEN: uma chamada de teste é permitida; se der certo, FECHA.
"""
from __future__ import annotations

import time


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, reset_timeout: float = 15.0):
        self.name = name
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "CLOSED"
        if time.monotonic() - self.opened_at >= self.reset_timeout:
            return "HALF_OPEN"
        return "OPEN"

    def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            raise CircuitOpenError(f"Circuito '{self.name}' aberto")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold or self.state == "HALF_OPEN":
                self.opened_at = time.monotonic()
            raise
        self.failures = 0
        self.opened_at = None
        return result
