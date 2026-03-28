"""Simple signed SVG captcha helpers for login and registration."""

from __future__ import annotations

import random
from datetime import timedelta
from urllib.parse import quote

from fastapi import HTTPException

from app.core.security import create_access_token, verify_token


CAPTCHA_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_LENGTH = 5
CAPTCHA_TTL_MINUTES = 10


def create_captcha_challenge() -> dict[str, str]:
    answer = "".join(random.choice(CAPTCHA_CHARSET) for _ in range(CAPTCHA_LENGTH))
    token = create_access_token(
        {
            "sub": "captcha",
            "kind": "captcha",
            "answer": answer.lower(),
        },
        expires_delta=timedelta(minutes=CAPTCHA_TTL_MINUTES),
    )
    return {
        "captcha_token": token,
        "svg_data_url": _build_captcha_svg_data_url(answer),
    }


def validate_captcha_or_raise(captcha_token: str, captcha_answer: str) -> None:
    payload = verify_token(captcha_token)
    normalized_answer = str(captcha_answer or "").strip().lower()
    if (
        not payload
        or payload.get("kind") != "captcha"
        or payload.get("sub") != "captcha"
        or not normalized_answer
        or normalized_answer != str(payload.get("answer") or "").strip().lower()
    ):
        raise HTTPException(status_code=400, detail="Invalid captcha")


def _build_captcha_svg_data_url(text: str) -> str:
    chars = list(text)
    colors = ["#1d4ed8", "#2563eb", "#0f172a", "#38bdf8", "#1e3a8a"]
    letter_markup = []
    for index, char in enumerate(chars):
        x = 24 + index * 28
        y = 44 + (index % 2) * 3
        rotate = (-8 + index * 4)
        fill = colors[index % len(colors)]
        letter_markup.append(
            f'<text x="{x}" y="{y}" transform="rotate({rotate} {x} {y})" '
            f'font-size="28" font-weight="800" font-family="Arial, sans-serif" fill="{fill}">{char}</text>'
        )

    sparkles = "".join(
        f'<circle cx="{18 + index * 18}" cy="{12 + (index % 3) * 12}" r="{2 + (index % 2)}" fill="#93c5fd" opacity="0.72" />'
        for index in range(8)
    )
    waves = (
        '<path d="M6 42C22 22 42 68 60 44C78 20 94 58 114 40C128 28 144 36 154 30" '
        'stroke="#60a5fa" stroke-width="3" stroke-linecap="round" opacity="0.55" fill="none" />'
        '<path d="M8 20C24 36 42 6 64 24C82 38 102 8 124 24C138 34 146 26 154 20" '
        'stroke="#cbd5e1" stroke-width="2.5" stroke-linecap="round" opacity="0.7" fill="none" />'
    )
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="160" height="56" viewBox="0 0 160 56" fill="none">
  <defs>
    <linearGradient id="captcha-bg" x1="8" y1="6" x2="152" y2="50" gradientUnits="userSpaceOnUse">
      <stop stop-color="#ffffff" />
      <stop offset="1" stop-color="#dbeafe" />
    </linearGradient>
  </defs>
  <rect x="1.5" y="1.5" width="157" height="53" rx="16" fill="url(#captcha-bg)" stroke="#bfdbfe" stroke-width="3" />
  {sparkles}
  {waves}
  {''.join(letter_markup)}
</svg>
""".strip()
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"
