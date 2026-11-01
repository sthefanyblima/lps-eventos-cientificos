"""Acesso a banco de dados relacional — um banco por microservice e por tenant.

Padrão *Database per Service*: cada microservice tem o seu próprio banco
MySQL e nenhum serviço lê o banco de outro (a comunicação é sempre via API).
Multi-tenancy no estilo do WISE (Tizzei et al., 2017): um banco por tenant,
chamado ``lps_<tenant>_<servico>`` (ex.: ``lps_sbes_2026_users``).

O SGBD vem da variável ``DATABASE_URL`` (template com ``{db}``)::

    mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}     # MySQL / MariaDB (padrão do projeto)
    sqlite:///data/{db}.db                              # alternativa sem servidor (testes)

As tabelas são criadas pelo ORM (SQLAlchemy) na primeira conexão, e os dados
de demonstração são inseridos se o banco estiver vazio.
"""
from __future__ import annotations

import os
import re
import threading
from contextlib import contextmanager
from typing import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import ROOT

DEFAULT_URL = "mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}"
_engines: dict[str, sessionmaker] = {}
_lock = threading.Lock()


def database_name(service: str, tenant: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", f"lps_{tenant}_{service}".lower())


def database_url(service: str, tenant: str) -> str:
    template = os.environ.get("DATABASE_URL", DEFAULT_URL)
    url = template.format(db=database_name(service, tenant))
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        path = ROOT / url.removeprefix("sqlite:///")
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    return url


def _ensure_database(url: str) -> None:
    """No MySQL, cria o banco do serviço/tenant se ainda não existir."""
    u = make_url(url)
    if not u.drivername.startswith("mysql"):
        return
    server = create_engine(u.set(database=""), pool_pre_ping=True)
    with server.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{u.database}` "
                          "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    server.dispose()


def session_factory(service: str, tenant: str, base: type[DeclarativeBase],
                    seed: Callable[[Session, str], None] | None = None) -> sessionmaker:
    key = f"{service}:{tenant}"
    with _lock:
        if key in _engines:
            return _engines[key]
        url = database_url(service, tenant)
        _ensure_database(url)
        engine: Engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
        base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        if seed:
            with factory() as s:
                seed(s, tenant)
                s.commit()
        _engines[key] = factory
        return factory


@contextmanager
def session_scope(service: str, tenant: str, base, seed=None):
    """Unidade de trabalho: abre sessão, faz commit no fim ou rollback em erro."""
    s: Session = session_factory(service, tenant, base, seed)()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
