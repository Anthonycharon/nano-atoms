"""UI builder agent: generate the visual theme for the current schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """你是一位专业 UI 设计师，根据应用结构生成视觉主题配置 JSON。
请严格按照以下格式输出，不要包含任何多余内容：

{
  "primary_color": "#颜色值（如 #6366f1）",
  "secondary_color": "#颜色值",
  "background_color": "#颜色值",
  "text_color": "#颜色值",
  "font_family": "字体名称",
  "border_radius": "圆角值（如 8px）",
  "spacing_unit": 4,
  "component_styles": {
    "组件ID": {
      "className": "Tailwind 类名字符串"
    }
  }
}

注意：颜色要专业大气，统一高辨识度，不要使用过深或过浅的配色。"""


async def run_ui_builder_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "ui_builder", "running")

    try:
        app_schema = state.get("app_schema")
        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("UI Builder Agent requires a valid app schema")

        llm = make_llm(temperature=0.4)
        app_context = build_app_context(state.get("app_type"))
        page_names = [page["name"] for page in app_schema.get("pages", [])]
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"{app_context}\n页面结构摘要："
                    f"{json.dumps({'title': app_schema.get('title'), 'pages': page_names}, ensure_ascii=False)}"
                )
            ),
        ])

        ui_theme = extract_json(response.content)
        if not isinstance(ui_theme, dict):
            raise ValueError("UI Builder Agent expected a JSON object response")
        summary = (
            f"主色 {ui_theme.get('primary_color', 'N/A')}，"
            f"字体 {ui_theme.get('font_family', 'N/A')}"
        )

        await notify_agent(cb, "ui_builder", "done", summary)
        return {**state, "ui_theme": ui_theme}

    except Exception as exc:
        message = f"UI Builder Agent failed: {exc}"
        await notify_agent(cb, "ui_builder", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
