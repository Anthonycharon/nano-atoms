"""Email verification and SMTP test helpers."""

from __future__ import annotations

import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import create_access_token, verify_token
from app.models import EmailVerificationCode, User


REGISTER_PURPOSE = "register"


def send_registration_code(session: Session, email: str) -> dict[str, int | str]:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email is required")
    _ensure_email_delivery_configured()

    existing_user = session.exec(select(User).where(User.email == normalized_email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    now = datetime.now(timezone.utc)
    latest = session.exec(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == REGISTER_PURPOSE,
        )
        .order_by(EmailVerificationCode.created_at.desc())
    ).first()
    latest_created_at = _as_utc(latest.created_at) if latest else None
    if latest_created_at and (now - latest_created_at).total_seconds() < settings.EMAIL_CODE_RESEND_SECONDS:
        retry_after = settings.EMAIL_CODE_RESEND_SECONDS - int((now - latest_created_at).total_seconds())
        raise HTTPException(status_code=429, detail=f"Please wait {retry_after}s before requesting another code")

    code = f"{secrets.randbelow(1_000_000):06d}"
    token_id = secrets.token_urlsafe(24)
    expires_at = now + timedelta(minutes=settings.EMAIL_CODE_EXPIRE_MINUTES)
    verification = EmailVerificationCode(
        email=normalized_email,
        purpose=REGISTER_PURPOSE,
        token_id=token_id,
        code_hash=_hash_code(code),
        expires_at=expires_at,
    )

    session.add(verification)
    session.commit()
    session.refresh(verification)

    try:
        _send_email_message(
            to_email=normalized_email,
            subject="Nano Atoms 注册验证码",
            text_content=(
                f"你的 Nano Atoms 注册验证码是 {code}。\n"
                f"验证码将在 {settings.EMAIL_CODE_EXPIRE_MINUTES} 分钟后失效。"
            ),
            html_content=(
                "<div style=\"font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;"
                "line-height:1.7;color:#0f172a\">"
                "<h2 style=\"margin:0 0 12px\">Nano Atoms 注册验证码</h2>"
                "<p style=\"margin:0 0 16px\">你正在注册 Nano Atoms 账号，请使用下面的验证码完成注册：</p>"
                f"<div style=\"display:inline-block;padding:12px 18px;border-radius:14px;"
                "background:#eff6ff;border:1px solid #bfdbfe;font-size:28px;font-weight:700;"
                f"letter-spacing:0.22em\">{code}</div>"
                f"<p style=\"margin:16px 0 0;color:#475569\">验证码将在 {settings.EMAIL_CODE_EXPIRE_MINUTES} 分钟后失效。</p>"
                "</div>"
            ),
        )
    except Exception as exc:
        session.delete(verification)
        session.commit()
        raise HTTPException(status_code=502, detail=f"Failed to send verification email: {exc}") from exc

    token = create_access_token(
        {
            "sub": normalized_email,
            "kind": "email_verification",
            "purpose": REGISTER_PURPOSE,
            "token_id": token_id,
        },
        expires_delta=timedelta(minutes=settings.EMAIL_CODE_EXPIRE_MINUTES),
    )
    return {
        "verification_token": token,
        "expires_in_seconds": settings.EMAIL_CODE_EXPIRE_MINUTES * 60,
        "resend_after_seconds": settings.EMAIL_CODE_RESEND_SECONDS,
    }


def validate_registration_code_or_raise(
    session: Session,
    *,
    email: str,
    verification_token: str,
    verification_code: str,
) -> None:
    normalized_email = str(email or "").strip().lower()
    payload = verify_token(verification_token)
    if (
        not payload
        or payload.get("kind") != "email_verification"
        or payload.get("purpose") != REGISTER_PURPOSE
        or str(payload.get("sub") or "").strip().lower() != normalized_email
        or not payload.get("token_id")
    ):
        raise HTTPException(status_code=400, detail="Invalid email verification")

    verification = session.exec(
        select(EmailVerificationCode).where(
            EmailVerificationCode.token_id == str(payload["token_id"]),
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.purpose == REGISTER_PURPOSE,
        )
    ).first()
    now = datetime.now(timezone.utc)
    verification_expires_at = _as_utc(verification.expires_at) if verification else None
    if not verification or verification.consumed_at is not None or not verification_expires_at or verification_expires_at <= now:
        raise HTTPException(status_code=400, detail="Email verification expired")

    if verification.code_hash != _hash_code(verification_code):
        raise HTTPException(status_code=400, detail="Invalid email verification code")

    verification.consumed_at = now
    session.add(verification)
    session.commit()


def send_test_email(to_email: str) -> dict[str, str]:
    normalized_email = str(to_email or "").strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Recipient email is required")
    _ensure_email_delivery_configured()

    sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    try:
        _send_email_message(
            to_email=normalized_email,
            subject="Nano Atoms SMTP 测试邮件",
            text_content=(
                "这是一封来自 Nano Atoms 的 SMTP 测试邮件。\n"
                f"发送时间：{sent_at}\n"
                "如果你收到了这封邮件，说明当前邮箱配置可用。"
            ),
            html_content=(
                "<div style=\"font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;"
                "line-height:1.7;color:#0f172a\">"
                "<h2 style=\"margin:0 0 12px\">Nano Atoms SMTP 测试邮件</h2>"
                "<p style=\"margin:0 0 12px\">如果你收到了这封邮件，说明当前 QQ 邮箱 SMTP 配置可用。</p>"
                f"<p style=\"margin:0;color:#475569\">发送时间：{sent_at}</p>"
                "</div>"
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send test email: {exc}") from exc

    return {"message": f"Test email sent to {normalized_email}"}


def _hash_code(code: str) -> str:
    normalized = str(code or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ensure_email_delivery_configured() -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise HTTPException(status_code=503, detail="Email delivery is not configured")


def _send_email_message(*, to_email: str, subject: str, text_content: str, html_content: str) -> None:
    message = EmailMessage()
    from_name = str(settings.SMTP_FROM_NAME or "").strip()
    from_email = settings.SMTP_FROM_EMAIL
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text_content)
    message.add_alternative(html_content, subtype="html")

    if settings.SMTP_USE_SSL:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            _smtp_login(server)
            server.send_message(message)
        return

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        _smtp_login(server)
        server.send_message(message)


def _smtp_login(server: smtplib.SMTP) -> None:
    username = str(settings.SMTP_USERNAME or "").strip()
    password = str(settings.SMTP_PASSWORD or "")
    if username:
        server.login(username, password)
