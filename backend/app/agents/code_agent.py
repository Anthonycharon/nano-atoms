"""Code agent: generate structured interaction logic for the schema."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """你是一位资深应用工程师，根据应用 Schema 生成交互逻辑 JSON（code_bundle）。
请严格按照以下格式输出，不要包含任何多余内容：

{
  "form_handlers": [
    {
      "form_id": "表单组件 ID",
      "fields": ["字段名列表"],
      "submit_action": "save_local",
      "validation": {"字段名": "required|email|phone 等规则"}
    }
  ],
  "data_bindings": [
    {
      "component_id": "组件 ID",
      "data_source": "local_state|form_data",
      "field_path": "字段路径"
    }
  ],
  "initial_state": {
    "键": "初始值"
  },
  "page_transitions": [
    {
      "from_page": "页面 ID",
      "to_page": "页面 ID",
      "trigger_component": "组件 ID"
    }
  ]
}

注意：不要包含任何实际可执行的 JavaScript 代码，只描述行为 JSON。"""


async def run_code_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "code", "running")

    try:
        app_schema = state.get("app_schema")
        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("Code Agent requires a valid app schema")

        llm = make_llm(temperature=0.2)
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"应用 Schema：{json.dumps(app_schema, ensure_ascii=False)}"),
        ])

        code_bundle = extract_json(response.content)
        if not isinstance(code_bundle, dict):
            raise ValueError("Code Agent expected a JSON object response")
        form_count = len(code_bundle.get("form_handlers", []))
        binding_count = len(code_bundle.get("data_bindings", []))
        summary = f"生成 {form_count} 个表单处理器，{binding_count} 个数据绑定"

        await notify_agent(cb, "code", "done", summary)
        return {
            **state,
            "code_bundle": code_bundle,
            "qa_retry_count": state.get("qa_retry_count", 0),
        }

    except Exception as exc:
        message = f"Code Agent failed: {exc}"
        await notify_agent(cb, "code", "error", message)
        return {**state, "errors": state.get("errors", []) + [message]}
