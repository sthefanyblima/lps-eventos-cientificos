"""Memory (Lu et al., 2024, seção 3.2).

* **Memória de curto prazo** — o que cabe no contexto da requisição: configuração
  (persona), eventos recentes da conversa e o contexto de trabalho (objetivo, plano).
* **Memória de longo prazo** (feature opcional *MemoriaLongoPrazo*) — fica fora do
  contexto, no banco do serviço: histórico de eventos e conhecimento acumulado
  sobre o usuário (ex.: último tema buscado, última sessão recomendada).
* **Memory retrieval** — seleciona da memória de longo prazo o que entra na curta.

Sem a feature *MemoriaLongoPrazo*, o agente só mantém uma janela curta em memória
do processo (perdida ao reiniciar o serviço) — variabilidade dentro do agente.
"""
from __future__ import annotations

from collections import defaultdict, deque

from common.config import has_feature
from common.database import session_scope

from .model import Base
from .repository import MemoryRepository

WINDOW = 6
_short: dict[tuple[str, int], deque] = defaultdict(lambda: deque(maxlen=WINDOW))


class ShortTermMemory:
    def __init__(self, tenant: str, user_id: int):
        self.key = (tenant, user_id)

    def recent(self) -> list[dict]:
        return list(_short[self.key])

    def add(self, role: str, text: str) -> None:
        _short[self.key].append({"role": role, "text": text})


class LongTermMemory:
    enabled = staticmethod(lambda: has_feature("MemoriaLongoPrazo"))

    def __init__(self, tenant: str, user_id: int):
        self.tenant, self.user_id = tenant, user_id

    def _tx(self):
        return session_scope("ai_agent", self.tenant, Base)

    def retrieve(self) -> dict:
        """Memory retrieval: eventos recentes + conhecimento do usuário."""
        if not self.enabled():
            return {"recent": [], "knowledge": {}, "events": 0}
        with self._tx() as s:
            repo = MemoryRepository(s)
            return {"recent": [{"role": e.papel, "text": e.texto} for e in repo.recent_events(self.user_id)],
                    "knowledge": repo.knowledge(self.user_id), "events": repo.count_events(self.user_id)}

    def store(self, user_text: str, agent_text: str, facts: dict[str, str]) -> None:
        if not self.enabled():
            return
        with self._tx() as s:
            repo = MemoryRepository(s)
            repo.add_event(self.user_id, "usuario", user_text)
            repo.add_event(self.user_id, "agente", agent_text)
            for k, v in facts.items():
                repo.put_knowledge(self.user_id, k, v)

    def forget(self) -> None:
        with self._tx() as s:
            MemoryRepository(s).forget(self.user_id)
        _short.pop((self.tenant, self.user_id), None)
