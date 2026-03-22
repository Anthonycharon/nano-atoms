"""Product agent: convert a user prompt into structured PRD JSON."""

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import build_app_context, extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """你是一位资深产品经理。根据用户的需求描述，输出结构化的产品规格 JSON。
必须严格按照以下 JSON 格式输出，不要输出任何其他内容：

{
  "pages": ["页面名称列表，如 Home, Form, Dashboard"],
  "features": ["功能点列表"],
  "user_flows": ["用户流程描述，如 用户填写表单 -> 提交 -> 看到成功页面"],
  "data_fields": ["数据字段列表，如 name, email, phone"],
  "app_title": "应用标题"
}"""


async def run_product_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "product", "running")

    try:
        llm = make_llm(temperature=0.3)
        app_context = build_app_context(state.get("app_type"))
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"{app_context}\n需求描述：{state['prompt']}"),
        ])

        prd_json = extract_json(response.content)
        if not isinstance(prd_json, dict):
            raise ValueError("Product Agent expected a JSON object response")
        summary = (
            f"识别 {len(prd_json.get('pages', []))} 个页面，"
            f"{len(prd_json.get('features', []))} 个功能点"
        )
        await notify_agent(cb, "product", "done", summary)
        return {**state, "prd_json": prd_json, "errors": state.get("errors", [])}

    except Exception as exc:
        message = f"Product Agent failed: {exc}"
        await notify_agent(cb, "product", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
