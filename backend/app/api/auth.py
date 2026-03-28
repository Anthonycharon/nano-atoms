from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models import User
from app.schemas.auth import (
    CaptchaResponse,
    EmailVerificationResponse,
    LoginRequest,
    RegisterRequest,
    SendRegisterCodeRequest,
    TokenResponse,
    UserResponse,
)
from app.services.captcha_service import create_captcha_challenge, validate_captcha_or_raise
from app.services.email_verification_service import (
    send_registration_code,
    validate_registration_code_or_raise,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """JWT 认证依赖注入，返回当前用户。"""
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register/send-code", response_model=EmailVerificationResponse)
def send_register_code(body: SendRegisterCodeRequest, session: Annotated[Session, Depends(get_session)]):
    payload = send_registration_code(session, str(body.email))
    return EmailVerificationResponse(**payload)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, session: Annotated[Session, Depends(get_session)]):
    normalized_email = str(body.email).strip().lower()
    validate_registration_code_or_raise(
        session,
        email=normalized_email,
        verification_token=body.verification_token,
        verification_code=body.verification_code,
    )
    existing = session.exec(select(User).where(User.email == normalized_email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=normalized_email, password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Annotated[Session, Depends(get_session)]):
    normalized_email = str(body.email).strip().lower()
    validate_captcha_or_raise(body.captcha_token, body.captcha_answer)
    user = session.exec(select(User).where(User.email == normalized_email)).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout():
    """客户端清除 Token 即可，服务端无状态。"""
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserResponse(id=current_user.id, email=current_user.email)


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    return CaptchaResponse(**create_captcha_challenge())
