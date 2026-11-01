"""Responsible AI plugins (Lu et al., 2024, seção 3.5).

* **Guardrails** de entrada (mascara dados pessoais e bloqueia tentativas de
  *prompt injection*), de execução (lista branca de ferramentas, limite de passos)
  e de saída (remove dados pessoais, limita tamanho).
* **Black box recorder** — registra entrada e saída de cada componente, com
  data e hora, no banco do serviço (``registro_caixa_preta``), para auditoria.
* **Explainer** — explica ao usuário o objetivo entendido, o plano, as
  ferramentas (microservices) usadas e o que veio da memória.
"""
from __future__ import annotations

import json
import re
import uuid

from common.database import session_scope

from .model import Base
from .repository import BlackBoxRepository

PII = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF removido]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[número de cartão removido]"),
    (re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"), "[telefone removido]"),
]
INJECTION = re.compile(r"(ignore|desconsidere|esqueça).{0,25}(instru|regras|anteriores)|system prompt|prompt do sistema|"
                       r"modo desenvolvedor|jailbreak", re.I)
MAX_INPUT, MAX_OUTPUT = 1000, 2500


class InputGuardrail:
    def apply(self, text: str) -> tuple[str, list[str], bool]:
        notes = []
        if INJECTION.search(text):
            return text, ["entrada bloqueada: tentativa de alterar as instruções do agente"], False
        clean = text[:MAX_INPUT]
        if len(text) > MAX_INPUT:
            notes.append(f"entrada truncada para {MAX_INPUT} caracteres")
        for rx, repl in PII:
            if rx.search(clean):
                clean = rx.sub(repl, clean)
                notes.append(f"dado pessoal mascarado na entrada: {repl}")
        return clean, notes, True


class ExecutionGuardrail:
    MAX_CALLS = 6

    def __init__(self, allowed: set[str]):
        self.allowed = allowed

    def check(self, tool, args: dict, n_calls: int) -> tuple[bool, str]:
        if tool.name not in self.allowed:
            return False, f"ferramenta '{tool.name}' fora da lista branca"
        if n_calls > self.MAX_CALLS:
            return False, "limite de chamadas de ferramentas excedido"
        return True, ""


class OutputGuardrail:
    def apply(self, text: str) -> tuple[str, list[str]]:
        notes = []
        for rx, repl in PII:
            if rx.search(text):
                text = rx.sub(repl, text)
                notes.append("dado pessoal removido da resposta")
        if len(text) > MAX_OUTPUT:
            text = text[:MAX_OUTPUT] + "…"
            notes.append("resposta truncada")
        return text, notes


class BlackBoxRecorder:
    def __init__(self, tenant: str, user_id: int):
        self.tenant, self.user_id = tenant, user_id
        self.request_id = uuid.uuid4().hex
        self.records: list[dict] = []

    def record(self, component: str, inp, out) -> None:
        dump = lambda x: x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
        self.records.append({"order": len(self.records) + 1, "component": component, "input": dump(inp), "output": dump(out)})

    def flush(self) -> None:
        with session_scope("ai_agent", self.tenant, Base) as s:
            BlackBoxRepository(s).save(self.request_id, self.user_id, self.records)

    @staticmethod
    def read(tenant: str, request_id: str) -> list[dict]:
        with session_scope("ai_agent", tenant, Base) as s:
            return [{"order": r.ordem, "component": r.componente, "input": r.entrada, "output": r.saida,
                     "at": r.criado_em.isoformat(sep=" ", timespec="seconds") if r.criado_em else ""}
                    for r in BlackBoxRepository(s).by_request(request_id)]


class Explainer:
    def explain(self, goal, plan: list[dict], tasks: list[dict], memory: dict, model: str, notes: list[str]) -> list[str]:
        out = [f"Objetivo entendido: {goal.intent}" + (f" {goal.entities}" if goal.entities else "") + "."]
        if plan:
            out.append("Plano: " + " → ".join(f"{i + 1}) {p['tool']}" for i, p in enumerate(plan)) + ".")
        for t in tasks:
            out.append(f"Passo {t['step']}: {t['tool']} no {t['service']}-service — {t['status']}.")
        if memory.get("knowledge"):
            out.append("Memória de longo prazo consultada: " + ", ".join(memory["knowledge"]) + ".")
        out.append(f"Modelo: {model}.")
        out += [f"Guardrail: {n}" for n in notes]
        return out
