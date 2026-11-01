"""Testes de integração com SQLite temporário, usando o banco real via SQLAlchemy."""

from uuid import uuid4

import pytest

from services.events.dto import SessionIn
from services.events.service import EventService
from services.submissions.dto import SubmissionIn
from services.submissions.service import SubmissionService
from services.users.dto import RegisterIn
from services.users.service import DomainError, UserService


@pytest.fixture
def db_tenant(tmp_path, monkeypatch):
    """Cria um arquivo de banco isolado para cada teste, sem precisar de MySQL."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/{{db}}.db")
    return f"dbtest_{uuid4().hex}"


def test_login_le_usuario_semeado_e_persiste_historico(db_tenant):
    service = UserService(db_tenant)

    login = service.login("ana@exemplo.edu.br", "senha123")
    user_id = login["user"]["id"]
    saved = service.add_history(user_id, session_id=987654, action="favorite")
    history = service.history(user_id)

    assert login["user"]["email"] == "ana@exemplo.edu.br"
    assert saved["user_id"] == user_id
    assert any(
        item["session_id"] == 987654 and item["action"] == "favorite"
        for item in history
    )


def test_cadastro_persiste_dados_normalizados_e_bloqueia_email_duplicado(db_tenant):
    service = UserService(db_tenant)
    data = RegisterIn(
        name="Carla Teste",
        email="  CARLA.DB@EXAMPLE.COM  ",
        password="senha123",
        role="autor",
        interests=["  IA ", "ia", "Engenharia de Software"],
    )

    created = service.register(data)
    saved = service.get(created["id"])

    assert saved["email"] == "carla.db@example.com"
    assert set(saved["interests"]) == {"ia", "engenharia de software"}

    duplicate = RegisterIn(
        name="Outra Carla",
        email="carla.db@example.com",
        password="senha123",
        role="participante",
    )
    with pytest.raises(DomainError) as exc:
        service.register(duplicate)
    assert exc.value.status == 409


def test_evento_persiste_sessao_trilha_e_tags(db_tenant):
    service = EventService(db_tenant)
    data = SessionIn(
        title="Sessão de Persistência",
        track="Banco de Dados",
        tags=["Banco", "Banco"],
        speaker="Carla Teste",
        day="2026-11-10",
        start="10:30",
        room="Sala 1",
        kind="Palestra",
    )

    created = service.create(data)
    loaded = service.get(created["id"])
    found = service.list_sessions(q="persistencia", day="2026-11-10")

    assert loaded["title"] == "Sessão de Persistência"
    assert loaded["track"] == "Banco de Dados"
    assert loaded["tags"] == ["banco"]
    assert [item["id"] for item in found] == [created["id"]]


def test_submissao_persiste_trabalho_coautores_e_palavras_chave(db_tenant, monkeypatch):
    import services.submissions.service as submissions_module

    # Impede apenas a chamada de notificação; a gravação SQL continua real.
    monkeypatch.setattr(submissions_module, "publish", lambda *args, **kwargs: None)
    service = SubmissionService(db_tenant)
    data = SubmissionIn(
        author_id=42,
        title="Persistência relacional com SQLAlchemy",
        abstract="Resumo do trabalho de teste.",
        authors="Ana Silva, Bruno Lima",
        keywords="LPS, banco de dados",
        format="ArtigoCompleto",
    )

    created = service.create(data)
    loaded = service.get(created["id"])
    by_author = service.list(author_id=42)

    assert loaded["status"] == "submitted"
    assert loaded["authors"] == "Ana Silva, Bruno Lima"
    assert loaded["keywords"] == "LPS, banco de dados"
    assert [item["id"] for item in by_author] == [created["id"]]
