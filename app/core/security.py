from datetime import timedelta

import jwt
from pwdlib import PasswordHash

from app.core import clock
from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("timing-equalization-password")


def create_token(user_id) -> str:
    cfg = get_settings()
    issued = clock.now()
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": issued,
            "exp": issued + timedelta(minutes=cfg.token_minutes),
            "iss": cfg.jwt_issuer,
            "aud": cfg.jwt_audience,
        },
        cfg.jwt_secret,
        algorithm="HS256",
    )


def decode_token(token: str) -> dict:
    cfg = get_settings()
    return jwt.decode(
        token,
        cfg.jwt_secret,
        algorithms=["HS256"],
        issuer=cfg.jwt_issuer,
        audience=cfg.jwt_audience,
        options={"require": ["sub", "iat", "exp", "iss", "aud"]},
    )
