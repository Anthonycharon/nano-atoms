"""Minimal LangGraph orchestration for direct page generation."""

from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .design_director_agent import run_design_director_agent
from .product_agent import run_product_agent


class AgentState(TypedDict):
    project_id: int
    version_id: int
    prompt: str
    app_type: str
    prd_json: Optional[dict]
    design_brief: Optional[dict]
    site_plan: Optional[dict]
    app_schema: Optional[dict]
    ui_theme: Optional[dict]
    code_bundle: Optional[dict]
    qa_result: Optional[dict]
    qa_retry_count: int
    errors: list[str]
    ws_callback: Optional[Any]


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("product", run_product_agent)
    graph.add_node("design_director", run_design_director_agent)
    graph.set_entry_point("product")
    graph.add_edge("product", "design_director")
    graph.add_edge("design_director", END)
    return graph.compile()


compiled_graph = build_graph()
