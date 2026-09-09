import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.schemas.api import AuthRequest, TokenOut
from app.services.store import Store

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: AuthRequest):
    if Store.get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(id=uuid.uuid4().hex, username=body.username,
                password_hash=hash_password(body.password))
    Store.create_user(user)
    return TokenOut(access_token=create_access_token(user.id), username=user.username)


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = Store.get_user_by_username(form.username)
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials")
    return TokenOut(access_token=create_access_token(user.id), username=user.username)