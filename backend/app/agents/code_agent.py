"""Code agent: generate structured interaction logic from site planning data."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """你是一位资深应用工程师。请根据应用规划、界面目标与兼容结构，生成一个 JSON 对象 `code_bundle`，不要输出任何额外说明。
输出格式：{
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

规则：
- 只输出 JSON 对象。
- 不要输出实际可执行的 JavaScript 代码，只描述运行逻辑与状态。
- 优先依据应用目标、表单流程、关键操作和导航关系生成逻辑。
- 兼容结构仅用于补充组件与界面 ID，不要把它当成唯一信息来源。"""


def _planning_payload(state: dict[str, Any]) -> dict[str, Any]:
    site_plan = state.get("site_plan") if isinstance(state.get("site_plan"), dict) else {}
    app_schema = state.get("app_schema") if isinstance(state.get("app_schema"), dict) else {}
    prd_json = state.get("prd_json") if isinstance(state.get("prd_json"), dict) else {}
    design_brief = state.get("design_brief") if isinstance(state.get("design_brief"), dict) else {}
    return {
        "site_plan": site_plan,
        "prd_json": prd_json,
        "design_brief": design_brief,
        "compat_schema": app_schema,
    }


async def run_code_agent(state: dict) -> dict:
    cb = state.get("ws_callback")
    await notify_agent(cb, "code", "running")

    try:
        app_schema = state.get("app_schema")
        site_plan = state.get("site_plan")
        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("Code Agent requires a valid compatibility schema")
        if not isinstance(site_plan, dict) or not site_plan.get("pages"):
            raise ValueError("Code Agent requires a valid site plan")

        llm = make_llm(temperature=0.2)
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"应用规划数据：{json.dumps(_planning_payload(state), ensure_ascii=False)}"),
            ]
        )

        code_bundle = extract_json(response.content)
        if not isinstance(code_bundle, dict):
            raise ValueError("Code Agent expected a JSON object response")

        summary = "已整理应用交互逻辑、状态流转与基础运行数据"

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
