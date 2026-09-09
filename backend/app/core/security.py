import hashlib
import datetime
import secrets

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.services.store import Store
from app.models.entities import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/login", auto_error=False
)

DEFAULT_LOCAL_USER = User(
    id="local",
    username="local",
    password_hash="",
    role="user",
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split(":", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == digest


def create_access_token(user_id: str) -> str:
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": user_id, "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> User:
    """Local, login-free mode.

    A valid bearer token (registered account) maps to that user. When there is
    no token — or the token is absent/invalid — the request falls back to the
    default local user, so the UI works without a login screen.
    """
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user = Store.get_user_by_id(payload.get("sub"))
            if user is not None:
                return user
        except jwt.PyJWTError:
            pass
    return DEFAULT_LOCAL_USER