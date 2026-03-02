from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.core.rate_limit import limiter
from app.dependencies import get_auth_service
from app.schemas.auth import RefreshTokenIn, TokenOut, UserCreateIn, UserOut
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(
    body: UserCreateIn,
    svc: AuthService = Depends(get_auth_service),
):
    return await svc.register(body.username, body.password)


@router.post("/auth/login", response_model=TokenOut)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    svc: AuthService = Depends(get_auth_service),
):
    return await svc.login(form.username, form.password)


@router.post("/auth/refresh", response_model=TokenOut)
async def refresh(
    body: RefreshTokenIn,
    svc: AuthService = Depends(get_auth_service),
):
    return await svc.refresh(body.refresh_token)
