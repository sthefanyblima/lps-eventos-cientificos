"""Testes extras de regras e componentes, sem SQL, banco ou chamadas externas."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from common.security import create_token, decode_token
from common.service import Caller
from components.agent import AgentContext, Goal, Step, agent_vp
from components.certificate import cert_vp
from components.notification import channel_vp
from components.payment import payment_vp
from components.recommendation import rec_vp
from components.review_policy import review_vp
from services.events.dto import SessionIn
from services.reviews.dto import ReviewIn
from services.submissions.dto import StatusIn, SubmissionIn
from services.users.dto import HistoryIn, RegisterIn


def test_cartao_de_teste_valido_e_aprovado_sem_expor_numero():
    card = payment_vp.create("CartaoCredito")

    result = card.charge(150.0, {}, {"card_number": "4111 1111 1111 1111"})

    assert result["status"] == "approved"
    assert result["amount"] == 150.0
    assert "final 1111" in result["details"]
    assert "4111 1111 1111 1111" not in result["details"]


def test_pix_fica_pendente_ate_confirmacao():
    pix = payment_vp.create("Pix")
    payment = pix.charge(75.5, {}, {})

    confirmed = pix.confirm(payment)

    assert payment["status"] == "pending"
    assert confirmed["status"] == "approved"
    assert payment["pix_code"].startswith("SIMULADO|PIX|")
    assert payment["pix_code"].endswith("|75.50")
    assert len(payment["txid"]) == 20


def test_inscricao_gratuita_nao_cobra_valor():
    payment = payment_vp.create("Gratuito").charge(150.0, {}, {})

    assert payment["status"] == "approved"
    assert payment["amount"] == 0.0


def test_popularidade_pesa_acoes_e_remove_sessao_ja_agendada():
    sessions = [
        {"id": 1, "title": "Sessão A"},
        {"id": 2, "title": "Sessão B"},
        {"id": 3, "title": "Sessão C"},
    ]
    history = [
        {"session_id": 1, "action": "view"},
        {"session_id": 2, "action": "agenda"},
        {"session_id": 2, "action": "favorite"},
    ]

    result = rec_vp.create("Popularidade").recommend(
        {"agenda": [2]}, sessions, history, k=3
    )

    assert [item["id"] for item in result] == [1, 3]
    assert result[0]["score"] == 0.2


def test_recomendacao_por_conteudo_ignora_acentos():
    sessions = [
        {"id": 1, "title": "Proteção de dados", "tags": ["segurança"], "track": ""},
        {"id": 2, "title": "Ensino de cálculo", "tags": ["educação"], "track": ""},
    ]

    result = rec_vp.create("BaseadaConteudo").recommend(
        {"interests": ["SEGURANÇA"], "history": []}, sessions, [], k=2
    )

    assert result[0]["id"] == 1
    assert "seguranca" in result[0]["reason"]


@pytest.mark.parametrize(
    ("variant", "authors_hidden", "reviewer_hidden"),
    [
        ("SimplesCego", False, True),
        ("DuploCego", True, True),
        ("Aberta", False, False),
    ],
)
def test_politica_de_revisao_aplica_visibilidade_correta(
    variant, authors_hidden, reviewer_hidden
):
    policy = review_vp.create(variant)
    submission = {"author_id": 2, "authors": "Ana Silva"}
    review = {"reviewer_id": 9, "reviewer_name": "Bruno Lima"}

    visible_submission = policy.submission_for_reviewer(submission)
    visible_review = policy.review_for_author(review)

    assert (visible_submission["author_id"] is None) is authors_hidden
    assert (visible_review["reviewer_id"] is None) is reviewer_hidden
    assert submission["author_id"] == 2
    assert review["reviewer_id"] == 9


def test_certificado_de_participacao_exige_inscricao_aprovada():
    issuer = cert_vp.create("CertParticipacao")
    user = {"id": 4, "name": "Ana Silva"}
    context = {
        "tenant": "evento-teste",
        "event": {"name": "Simpósio de Teste"},
        "agenda": [{"id": 1}, {"id": 2}],
    }

    assert issuer.eligible(user, {**context, "registration": None}) == []
    assert issuer.eligible(
        user, {**context, "registration": {"status": "pending"}}
    ) == []

    certificates = issuer.eligible(
        user, {**context, "registration": {"status": "approved"}}
    )

    assert len(certificates) == 1
    assert certificates[0]["hours"] == 4
    assert certificates[0]["type"] == "Participação"
    assert len(certificates[0]["code"]) == 16


def test_certificado_de_apresentacao_somente_para_trabalho_aceito():
    issuer = cert_vp.create("CertApresentacao")
    certificates = issuer.eligible(
        {"id": 4, "name": "Ana Silva"},
        {
            "tenant": "evento-teste",
            "event": {"name": "Simpósio de Teste"},
            "submissions": [
                {
                    "id": 1,
                    "title": "Trabalho aceito",
                    "authors": "Ana Silva",
                    "status": "accepted",
                    "format": "ArtigoCompleto",
                },
                {
                    "id": 2,
                    "title": "Trabalho em revisão",
                    "authors": "Ana Silva",
                    "status": "under_review",
                    "format": "ResumoExpandido",
                },
            ],
        },
    )

    assert len(certificates) == 1
    assert '"Trabalho aceito"' in certificates[0]["text"]
    assert certificates[0]["hours"] == 1


def test_canais_de_notificacao_chamam_o_destino_injetado():
    sent_email = []
    in_app_messages = []
    user = {"id": 12, "email": "ana@example.com"}
    email = channel_vp.create(
        "Email", mail_store=lambda *args: sent_email.append(args)
    )
    in_app = channel_vp.create(
        "InApp", store=lambda *args: in_app_messages.append(args)
    )

    email_result = email.send(user, "Confirmação", "Inscrição confirmada")
    app_result = in_app.send(user, "Agenda", "Sessão adicionada")

    assert email_result == {"channel": "Email", "to": "ana@example.com", "delivered": True}
    assert sent_email == [("ana@example.com", "Confirmação", "Inscrição confirmada")]
    assert app_result == {"channel": "InApp", "delivered": True}
    assert in_app_messages == [(12, "Agenda", "Sessão adicionada")]


def test_usuario_pode_acessar_proprios_dados():
    Caller(user_id=7, role="participante").ensure_self_or(7)


def test_usuario_nao_pode_acessar_dados_de_outra_pessoa():
    with pytest.raises(HTTPException) as exc:
        Caller(user_id=7, role="participante").ensure_self_or(8)

    assert exc.value.status_code == 403


def test_organizador_pode_acessar_dados_de_outra_pessoa():
    Caller(user_id=1, role="organizador").ensure_self_or(8, "organizador")


def test_participante_nao_pode_usar_rota_de_organizador():
    with pytest.raises(HTTPException) as exc:
        Caller(user_id=7, role="participante").ensure_role("organizador")

    assert exc.value.status_code == 403


@pytest.mark.parametrize("action", ["view", "favorite", "agenda"])
def test_historico_aceita_acoes_previstas(action):
    entry = HistoryIn(session_id=1, action=action)

    assert entry.action == action


def test_historico_recusa_acao_desconhecida():
    with pytest.raises(ValidationError):
        HistoryIn(session_id=1, action="delete")


def test_cadastro_recusa_papel_nao_permitido():
    with pytest.raises(ValidationError):
        RegisterIn(
            name="Ana Silva",
            email="ana@example.com",
            password="senha123",
            role="admin",
        )


def test_sessao_recusa_titulo_curto_e_formato_de_horario_invalido():
    with pytest.raises(ValidationError):
        SessionIn(title="AB", day="2026-11-10", start="09:00")

    with pytest.raises(ValidationError):
        SessionIn(title="Palestra", day="2026-11-10", start="9h")


@pytest.mark.parametrize("score", [-3, -2, -1, 0, 1, 2, 3])
def test_parecer_aceita_notas_dentro_da_escala(score):
    review = ReviewIn(submission_id=5, reviewer_id=8, score=score)

    assert review.score == score


@pytest.mark.parametrize("score", [-4, 4])
def test_parecer_recusa_notas_fora_da_escala(score):
    with pytest.raises(ValidationError):
        ReviewIn(submission_id=5, reviewer_id=8, score=score)


@pytest.mark.parametrize("status", ["submitted", "under_review", "accepted", "rejected"])
def test_status_de_submissao_aceita_valores_previstos(status):
    assert StatusIn(status=status).status == status


def test_status_de_submissao_recusa_valor_desconhecido():
    with pytest.raises(ValidationError):
        StatusIn(status="published")


def test_dto_recusa_submissao_com_titulo_curto():
    with pytest.raises(ValidationError):
        SubmissionIn(author_id=4, title="Oi", authors="Ana", format="ArtigoCompleto")


def test_token_jwt_carrega_identidade_e_tenant():
    token = create_token(7, "autor", "Bruno", "sbes-2026")

    claims = decode_token(token)

    assert claims["sub"] == "7"
    assert claims["role"] == "autor"
    assert claims["name"] == "Bruno"
    assert claims["tenant"] == "sbes-2026"


def test_agente_local_resolve_referencia_de_resultado_anterior():
    calls = []
    steps = [
        Step("listar_sessoes", {}, "buscar opções"),
        Step("selecionar_sessao", {"session_id": "$1.items[0].id"}, "usar primeira opção"),
    ]

    def execute(tool, args, why):
        calls.append((tool, args, why))
        if tool == "listar_sessoes":
            return {"items": [{"id": 42}]}
        return {"selected_id": args["session_id"]}

    context = AgentContext(
        goal=Goal("Escolha uma sessão", "agenda"),
        persona={},
        prompt="",
        memory={},
        tools={},
        execute=execute,
        plan_generator=lambda goal, tools, memory: steps,
        respond=lambda goal, results, memory: f"Sessão {results[-1]['output']['selected_id']}",
    )

    result = agent_vp.create("AgenteLocal").solve(context)

    assert calls[1][1] == {"session_id": 42}
    assert result["answer"] == "Sessão 42"
    assert len(result["plan"]) == 2