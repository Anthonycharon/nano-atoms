"""
LangGraph 多智能体编排图。
节点流：product → architect → ui_builder → code → qa → END
QA 仅作建议性审查，不触发重试，结果始终流向 END。
"""
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .architect_agent import run_architect_agent
from .code_agent import run_code_agent
from .design_director_agent import run_design_director_agent
from .product_agent import run_product_agent
from .qa_agent import run_qa_agent
from .ui_builder_agent import run_ui_builder_agent


class AgentState(TypedDict):
    """LangGraph 状态机共享状态。"""
    project_id: int
    version_id: int
    prompt: str
    app_type: str
    # 各 Agent 产物
    prd_json: Optional[dict]
    design_brief: Optional[dict]
    app_schema: Optional[dict]
    ui_theme: Optional[dict]
    code_bundle: Optional[dict]
    qa_result: Optional[dict]
    # 控制字段
    qa_retry_count: int
    errors: list[str]
    # WebSocket 回调（不持久化，仅运行时传递）
    ws_callback: Optional[Any]


def build_graph() -> StateGraph:
    """构建并编译 LangGraph 状态图。"""
    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("product", run_product_agent)
    graph.add_node("design_director", run_design_director_agent)
    graph.add_node("architect", run_architect_agent)
    graph.add_node("ui_builder", run_ui_builder_agent)
    graph.add_node("code", run_code_agent)
    graph.add_node("qa", run_qa_agent)

    # 线性链路：QA 仅作建议，始终流向 END
    graph.set_entry_point("product")
    graph.add_edge("product", "design_director")
    graph.add_edge("design_director", "architect")
    graph.add_edge("architect", "ui_builder")
    graph.add_edge("ui_builder", "code")
    graph.add_edge("code", "qa")
    graph.add_edge("qa", END)

    return graph.compile()


# 模块级单例，避免每次调用重建
compiled_graph = build_graph()
