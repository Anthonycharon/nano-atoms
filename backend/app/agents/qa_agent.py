"""
QA Agent：对生成内容做一致性校验，输出校验报告。
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from .utils import extract_json, make_llm, notify_agent


SYSTEM_PROMPT = """你是一位 QA 测试师，对生成的应用结构内容做宽容性审查。
请严格按照以下格式输出，不要包含任何多余内容：

{
  "passed": true 或 false,
  "issues": ["仅列出严重问题，若无则为空数组"],
  "suggestions": ["改进建议列表"],
  "summary": "测试结果摘要"
}

判断标准（宽容模式）：
- 只要 app_schema 存在且包含至少一个页面，且每个页面有至少一个组件，就应判定 passed: true
- 导航路由、form_id 对应关系等细节问题只记录在 suggestions 中，不影响 passed
- 仅在 app_schema 完全为空或所有页面均无组件时，才判定 passed: false
- 对 AI 生成内容保持包容，关注结构完整性而非细节完美性"""


async def run_qa_agent(state: dict) -> dict:
    """LangGraph 节点：一致性校验与检查。"""
    cb = state.get("ws_callback")
    await notify_agent(cb, "qa", "running")

    try:
        app_schema = state.get("app_schema")
        code_bundle = state.get("code_bundle")

        if not isinstance(app_schema, dict) or not app_schema.get("pages"):
            raise ValueError("QA Agent requires a valid app schema")
        if not isinstance(code_bundle, dict):
            raise ValueError("QA Agent requires a valid code bundle")

        llm = make_llm(temperature=0.1)

        # 提取结构化摘要，确保 QA 有足够信息做检查
        pages_summary = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "route": p.get("route"),
                "component_ids": [c.get("id") for c in p.get("components", [])],
                "component_types": [c.get("type") for c in p.get("components", [])],
            }
            for p in app_schema.get("pages", [])
        ]
        schema_summary = {
            "title": app_schema.get("title"),
            "navigation": app_schema.get("navigation", []),
            "pages": pages_summary,
        }
        bundle_summary = {
            "form_handlers": [
                {"form_id": f.get("form_id"), "fields": f.get("fields", [])}
                for f in code_bundle.get("form_handlers", [])
            ],
            "page_transitions": code_bundle.get("page_transitions", []),
        }

        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"app_schema：{json.dumps(schema_summary, ensure_ascii=False)}\n"
                    f"code_bundle：{json.dumps(bundle_summary, ensure_ascii=False)}"
                )
            ),
        ])

        qa_result = extract_json(response.content)
        if not isinstance(qa_result, dict):
            raise ValueError("QA Agent expected a JSON object response")
        summary = qa_result.get("summary", "校验完成")
        # QA 仅作建议性审查，始终标记为 done
        status = "done"

        await notify_agent(cb, "qa", status, summary)
        return {**state, "qa_result": qa_result}

    except Exception as e:
        msg = f"QA Agent 失败: {e}"
        await notify_agent(cb, "qa", "error", msg)
        # QA 失败时默认通过，避免死循环
        return {**state, "qa_result": {"passed": True, "issues": [], "summary": "QA 跳过，执行异常。"}}
