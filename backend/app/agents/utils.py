"""Shared helpers for agent execution."""

import json
import re
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings


def extract_json(text: str) -> Any:
    """Extract JSON content from raw LLM output."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for code_block in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text):
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    balanced_object = _extract_balanced_json_object(text)
    if balanced_object is not None:
        try:
            return json.loads(balanced_object)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Unable to extract valid JSON from LLM output: {text[:200]}")


def _extract_balanced_json_object(text: str) -> str | None:
    """Extract the first balanced top-level JSON object substring from text."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def make_llm(temperature: float = 0.3) -> ChatOpenAI:
    """Create a shared ChatOpenAI client."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=1,
    )


def infer_content_language(text: str | None) -> str:
    """Infer the primary content language from a user prompt."""
    raw = str(text or "")
    if re.search(r"[\u4e00-\u9fff]", raw):
        return "zh-CN"
    if re.search(r"[\u3040-\u30ff]", raw):
        return "ja-JP"
    if re.search(r"[\uac00-\ud7af]", raw):
        return "ko-KR"
    return "en-US"


def build_content_language_instruction(language: str | None) -> str:
    """Build a strict user-facing copy instruction for downstream prompts."""
    normalized = str(language or "").strip().lower()
    if normalized == "zh-cn":
        return (
            "All user-facing copy must be written in Simplified Chinese, including page names, "
            "navigation labels, headings, descriptions, button text, placeholders, sample data labels, "
            "and helper text. Keep JSON keys in English when needed, but all visible content must be Chinese."
        )
    if normalized == "ja-jp":
        return (
            "All user-facing copy must be written in Japanese, including page names, navigation labels, "
            "headings, descriptions, button text, placeholders, and helper text."
        )
    if normalized == "ko-kr":
        return (
            "All user-facing copy must be written in Korean, including page names, navigation labels, "
            "headings, descriptions, button text, placeholders, and helper text."
        )
    return (
        "All user-facing copy must be written in clear English, including page names, navigation labels, "
        "headings, descriptions, button text, placeholders, and helper text."
    )


def build_app_context(app_type: Optional[str]) -> str:
    """Build a prompt hint without forcing users to choose a fixed app type."""
    normalized = (app_type or "").strip().lower()
    if normalized in ("", "auto"):
        return (
            "项目类型：自动推断。请完全依据需求内容判断应用形态，"
            "不要被固定网页类型限制；如果需求更偏后端或全栈，也以最合适的方向理解。"
        )

    return f"项目类型参考：{app_type}。如果它与需求本身冲突，以需求描述为准。"


async def notify_agent(
    ws_callback: Optional[object],
    agent_name: str,
    status: str,
    summary: Optional[str] = None,
) -> None:
    """Safely invoke the websocket callback when it exists."""
    if ws_callback and callable(ws_callback):
        await ws_callback(agent_name, status, summary)
