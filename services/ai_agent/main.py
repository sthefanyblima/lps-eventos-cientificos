"""AI Agent Service · porta 8009 — Feature **Assistente com Agente de IA** (opcional, Agentic AI).

Implementa a arquitetura de referência para agentes baseados em modelos de
fundação de Lu et al. (CSIRO, 2024): interaction engineering, memória (curto e
longo prazo), planejamento, execution engine (ferramentas = microservices do
produto), plugins de IA responsável (guardrails, black box recorder, explainer)
e camada de modelos — esta última é o ponto de variação **Provedor** (xor):
AgenteLLM (Claude, tool use) | AgenteLocal (regras). Feature opcional
**MemoriaLongoPrazo** ativa a memória persistente no MySQL.
"""
from common.service import create_service

from .controller import router

app = create_service("ai_agent", "AI Agent Service", __doc__, router, bindings=["ai_provider"])
