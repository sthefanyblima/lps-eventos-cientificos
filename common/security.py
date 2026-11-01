"""Segurança: hash de senha (PBKDF2-SHA256) e tokens JWT (HS256).

O Users Service emite o token no login; o API Gateway o valida antes de
encaminhar requisições protegidas e repassa a identidade aos microservices
nos cabeçalhos ``X-User-Id`` e ``X-User-Role``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

import jwt

SECRET = os.environ.get("JWT_SECRET", "lps-eventos-dev-secret-troque-em-producao")
ALGORITHM = "HS256"
TOKEN_TTL = 8 * 3600
ITERATIONS = 120_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iters))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except ValueError:
        return False


def create_token(user_id: int, role: str, name: str, tenant: str) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "role": role, "name": name, "tenant": tenant, "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Retorna as claims ou lança ``jwt.InvalidTokenError``."""
    return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
