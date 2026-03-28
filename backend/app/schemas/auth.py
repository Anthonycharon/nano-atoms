from pydantic import BaseModel, EmailStr


class CaptchaRequestMixin(BaseModel):
    captcha_token: str
    captcha_answer: str


class SendRegisterCodeRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    verification_token: str
    verification_code: str


class LoginRequest(CaptchaRequestMixin):
    email: EmailStr
    password: str


class CaptchaResponse(BaseModel):
    captcha_token: str
    svg_data_url: str


class EmailVerificationResponse(BaseModel):
    verification_token: str
    expires_in_seconds: int
    resend_after_seconds: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
