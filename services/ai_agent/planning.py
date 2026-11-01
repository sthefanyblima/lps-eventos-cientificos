"""Planning (Lu et al., 2024, seção 3.3).

* **Single-path plan generator** — cada passo tem um único sucessor (como
  Chain-of-Thought), gerado de uma só vez (*one-shot*). Passos podem usar o
  resultado do anterior (``"$1.0.id"`` = id do 1º item devolvido pelo passo 1).
* **Plan reflection (self-reflection)** — o agente revisa o próprio plano antes
  de executar: remove passos cujas ferramentas não existem neste produto e limita
  o tamanho do plano.
"""
from __future__ import annotations

from components.agent import Goal, Step

MAX_STEPS = 4


class SinglePathPlanGenerator:
    def generate(self, goal: Goal, tools: dict, memory: dict) -> list[Step]:
        e = goal.entities
        if goal.intent == "recomendar":
            plan = [Step("recomendar_sessoes", {"k": 3}, "obter sessões compatíveis com o perfil e o histórico")]
            if e.get("add_to_agenda"):
                plan.append(Step("adicionar_agenda", {"session_id": "$1.0.id"}, "adicionar a melhor recomendação à agenda"))
            return plan
        if goal.intent == "buscar":
            return [Step("buscar_sessoes", {"query": e.get("query", "")}, "procurar o tema na programação")]
        if goal.intent == "adicionar_agenda":
            if e.get("session_id"):
                return [Step("adicionar_agenda", {"session_id": e["session_id"]}, "adicionar a sessão pedida")]
            return [Step("recomendar_sessoes", {"k": 1}, "nenhuma sessão indicada: escolher a melhor recomendação"),
                    Step("adicionar_agenda", {"session_id": "$1.0.id"}, "adicionar a sessão recomendada")]
        if goal.intent == "minha_agenda":
            return [Step("minha_agenda", {}, "consultar a agenda pessoal")]
        if goal.intent == "submissoes":
            return [Step("status_submissoes", {}, "consultar o status das submissões")]
        if goal.intent == "memoria":
            return [Step("meu_perfil", {}, "ler interesses cadastrados no perfil")]
        return []


class PlanReflection:
    def reflect(self, plan: list[Step], tools: dict) -> tuple[list[Step], list[str]]:
        notes, kept = [], []
        for s in plan:
            if s.tool not in tools:
                notes.append(f"passo '{s.tool}' removido: ferramenta indisponível neste produto")
            else:
                kept.append(s)
        if len(kept) > MAX_STEPS:
            notes.append(f"plano truncado para {MAX_STEPS} passos")
            kept = kept[:MAX_STEPS]
        return kept, notes
