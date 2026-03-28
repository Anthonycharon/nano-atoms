"""Product agent: convert a user prompt into structured PRD JSON."""

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import (
    build_app_context,
    build_content_language_instruction,
    extract_json,
    infer_content_language,
    make_llm,
    notify_agent,
)


SYSTEM_PROMPT = """You are a senior product manager.
Convert the user request into one JSON object only, with no markdown or commentary.

Output format:
{
  "pages": ["page names such as Home, Login, Dashboard"],
  "features": ["feature list"],
  "user_flows": ["user flow descriptions"],
  "data_fields": ["field names such as email, password, company_name"],
  "app_title": "application title",
  "content_language": "zh-CN | en-US | ja-JP | ko-KR",
  "visual_preferences": {
    "theme_mode": "light | dark | mixed | auto",
    "color_story": "short phrase describing the color direction",
    "style_keywords": ["keyword", "keyword"],
    "must_have": ["explicit visual requirements from the user"],
    "avoid": ["styles the user does not want"]
  }
}

Rules:
- Preserve explicit visual instructions from the user, including dark mode, black backgrounds, minimalism, brutalism, glass, luxury, playful, editorial, or sci-fi.
- If the user names a color or mood, keep it in visual_preferences instead of replacing it with a generic SaaS style.
- Detect the user's content language and store it in content_language.
- Keep page names and app_title in the same language the user is using unless they explicitly ask for a different language.
- If the user gives no visual direction, set theme_mode to "auto" and keep style_keywords practical rather than generic."""


async def run_product_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "product", "running")

    try:
        llm = make_llm(temperature=0.3)
        app_context = build_app_context(state.get("app_type"))
        prompt = state["prompt"]
        content_language = infer_content_language(prompt)
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"{app_context}\n"
                        f"{build_content_language_instruction(content_language)}\n"
                        f"Preferred content language: {content_language}\n"
                        f"User prompt: {prompt}"
                    )
                ),
            ]
        )

        prd_json = extract_json(response.content)
        if not isinstance(prd_json, dict):
            raise ValueError("Product Agent expected a JSON object response")
        prd_json["content_language"] = str(prd_json.get("content_language") or content_language)
        summary = f"已完成需求梳理，并提炼 {len(prd_json.get('features', []))} 个核心能力点"
        await notify_agent(cb, "product", "done", summary)
        return {**state, "prd_json": prd_json, "errors": state.get("errors", [])}

    except Exception as exc:
        message = f"Product Agent failed: {exc}"
        await notify_agent(cb, "product", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
