from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from app.models.usuario import Usuario
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    UserInfo,
    UserProfile,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Usuario).where(Usuario.codigo_empleado == payload.codigo_empleado)
    )
    user = result.scalars().first()

    if (
        not user
        or not user.activo
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código de empleado o contraseña incorrectos.",
        )

    token_data = {"sub": str(user.id)}

    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=UserInfo(id=user.id, nombre=user.nombre, rol=user.rol.value),
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Renovar sesión",
)
async def refresh_session(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="La sesión no puede renovarse.",
    )
    try:
        token_payload = jwt.decode(
            payload.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if token_payload.get("type") != "refresh":
            raise credentials_exception
        user_id = int(token_payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalars().first()
    if not user or not user.activo:
        raise credentials_exception

    token_data = {"sub": str(user.id)}
    return RefreshTokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserProfile, summary="Perfil del usuario autenticado")
async def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user
