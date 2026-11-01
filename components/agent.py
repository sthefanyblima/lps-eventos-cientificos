"""Ponto de variação **Provedor do Agente de IA** (xor): AgenteLLM | AgenteLocal.

Na arquitetura de referência de agentes de Lu et al. (CSIRO/Data61, 2024), este
componente corresponde à camada **AI models** e à forma de **planejamento**:

* ``AgenteLLM``   — *external FM* (Claude, Messages API com tool use) com
  *incremental model querying*: o modelo é consultado a cada passo e decide a
  próxima ferramenta a chamar.
* ``AgenteLocal`` — *non-FM model* (regras): usa o *single-path plan generator*
  determinístico do serviço, que gera o plano inteiro de uma vez
  (*one-shot*) e o executa passo a passo.

Os dois recebem o mesmo :class:`AgentContext`, ou seja, as mesmas ferramentas
(operações dos microservices do produto), a mesma memória e os mesmos
guardrails. Isso torna o provedor intercambiável, como em toda variante de LPS.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from .base import VariationPoint


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict                 # JSON Schema
    fn: Callable[..., object]
    feature: str                     # feature de que a ferramenta depende
    service: str                     # microservice que a ferramenta chama


@dataclass
class Goal:
    """Saída do *passive goal creator*: intenção + parâmetros extraídos do pedido."""
    text: str
    intent: str
    entities: dict = field(default_factory=dict)


@dataclass
class Step:
    tool: str
    args: dict
    why: str


@dataclass
class AgentContext:
    """Tudo o que o provedor pode usar — montado pelo serviço do agente."""
    goal: Goal
    persona: dict
    prompt: str                                  # gerado pelo prompt/response generator
    memory: dict                                 # visão da memória (curta + longa)
    tools: dict[str, Tool]                       # registro de ferramentas já filtrado pelo produto
    execute: Callable[[str, dict, str], Any]     # executor (guardrail + monitor + caixa-preta)
    plan_generator: Callable[[Goal, dict, dict], list[Step]]
    respond: Callable[[Goal, list[dict], dict], str]   # gerador de resposta (templates)


class AgentProvider(ABC):
    label = "?"
    querying = "?"

    @abstractmethod
    def solve(self, ctx: AgentContext) -> dict:
        """Retorna {answer, plan: [{tool, args, why}], model}."""


agent_vp: VariationPoint[AgentProvider] = VariationPoint("ai_provider", AgentProvider)


@agent_vp.variant("AgenteLocal")
class LocalRuleAgent(AgentProvider):
    """Non-FM model: plano de caminho único gerado por regras e executado em sequência."""
    label = "Agente local (regras)"
    querying = "one-shot (plano gerado de uma vez)"

    def solve(self, ctx: AgentContext) -> dict:
        plan = ctx.plan_generator(ctx.goal, ctx.tools, ctx.memory)
        results = []
        for i, step in enumerate(plan):
            args = _resolve(step.args, results)
            out = ctx.execute(step.tool, args, step.why)
            results.append({"step": i + 1, "tool": step.tool, "args": args, "output": out})
        answer = ctx.respond(ctx.goal, results, ctx.memory)
        return {"answer": answer, "plan": [s.__dict__ for s in plan], "model": self.label}


@agent_vp.variant("AgenteLLM")
class LLMAgent(AgentProvider):
    """External FM (Claude): consulta incremental com tool use. Sem chave, cai para o agente local."""
    label = "Agente LLM (Claude)"
    querying = "incremental (o modelo decide cada passo)"
    API = "https://api.anthropic.com/v1/messages"
    MAX_STEPS = 6

    def solve(self, ctx: AgentContext) -> dict:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            res = LocalRuleAgent().solve(ctx)
            res["model"] = self.label + " — sem ANTHROPIC_API_KEY, fallback para o agente local"
            return res
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        tool_specs = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in ctx.tools.values()]
        messages = [{"role": "user", "content": ctx.goal.text}]
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        plan: list[dict] = []
        for _ in range(self.MAX_STEPS):
            r = httpx.post(self.API, headers=headers, timeout=60, json={
                "model": model, "max_tokens": 1024, "system": ctx.prompt, "tools": tool_specs, "messages": messages})
            r.raise_for_status()
            data = r.json()
            messages.append({"role": "assistant", "content": data["content"]})
            calls = [b for b in data["content"] if b["type"] == "tool_use"]
            if data.get("stop_reason") != "tool_use" or not calls:
                text = "".join(b.get("text", "") for b in data["content"] if b["type"] == "text")
                return {"answer": text, "plan": plan, "model": f"{self.label} ({model})"}
            results = []
            for c in calls:
                args = c.get("input", {})
                plan.append({"tool": c["name"], "args": args, "why": "escolhido pelo modelo"})
                try:
                    out = ctx.execute(c["name"], args, "escolhido pelo modelo")
                except Exception as exc:                 # erro (ou bloqueio de guardrail) volta ao modelo
                    out = {"error": str(exc)}
                results.append({"type": "tool_result", "tool_use_id": c["id"],
                                "content": json.dumps(out, ensure_ascii=False, default=str)[:6000]})
            messages.append({"role": "user", "content": results})
        return {"answer": "Limite de passos do agente atingido.", "plan": plan, "model": self.label}


def _resolve(args: dict, results: list[dict]) -> dict:
    """Substitui referências a resultados anteriores, ex.: ``"$1.items[0].id"``."""
    out = {}
    for k, v in args.items():
        if isinstance(v, str) and v.startswith("$"):
            ref, _, path = v[1:].partition(".")
            val: Any = results[int(ref) - 1]["output"] if results else None
            for part in filter(None, path.replace("]", "").replace("[", ".").split(".")):
                val = val[int(part)] if part.isdigit() else (val or {}).get(part)
                if val is None:
                    break
            out[k] = val
        else:
            out[k] = v
    return out
