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

    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_block:
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

    raise ValueError(f"Unable to extract valid JSON from LLM output: {text[:200]}")


def make_llm(temperature: float = 0.3) -> ChatOpenAI:
    """Create a shared ChatOpenAI client."""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
        timeout=120,
        max_retries=1,
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
