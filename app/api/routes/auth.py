from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import Session
from app.schemas.auth import RegisterRequest, TokenRead
from app.schemas.user import UserRead
from app.services.auth import login, register

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(data: RegisterRequest, session: Session):
    return await register(session, data)


@router.post("/token", response_model=TokenRead)
async def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: Session):
    return await login(session, form.username, form.password)
