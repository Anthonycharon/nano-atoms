"""
P1 功能：模板系统。
提供 5 个预置模板，每个含默认 Schema、示例 Prompt 和应用类型。
"""
from typing import Any


TEMPLATES: dict[str, dict[str, Any]] = {
    "留资表单": {
        "app_type": "form",
        "example_prompt": "做一个用户留资表单，收集姓名、手机、公司、职位信息，提交后显示感谢页",
        "default_schema": {
            "app_id": "tpl_lead_form",
            "title": "留资表单",
            "app_type": "form",
            "pages": [
                {
                    "id": "page_form",
                    "name": "填写信息",
                    "route": "/",
                    "components": [
                        {"id": "h1", "type": "heading", "props": {"text": "请填写您的信息"}, "children": [], "actions": []},
                        {"id": "form1", "type": "form", "props": {}, "children": [
                            {"id": "inp_name", "type": "input", "props": {"label": "姓名", "name": "name", "placeholder": "请输入姓名", "form_id": "form1"}, "children": [], "actions": []},
                            {"id": "inp_phone", "type": "input", "props": {"label": "手机", "name": "phone", "placeholder": "请输入手机号", "type": "tel", "form_id": "form1"}, "children": [], "actions": []},
                            {"id": "inp_company", "type": "input", "props": {"label": "公司", "name": "company", "placeholder": "请输入公司名称", "form_id": "form1"}, "children": [], "actions": []},
                            {"id": "btn_submit", "type": "button", "props": {"label": "提交"}, "children": [], "actions": [{"trigger": "click", "type": "submit_form", "payload": {"form_id": "form1"}}]},
                        ], "actions": []},
                    ],
                }
            ],
            "ui_theme": {
                "primary_color": "#6366f1",
                "secondary_color": "#a5b4fc",
                "background_color": "#ffffff",
                "text_color": "#111827",
                "font_family": "sans-serif",
                "border_radius": "8px",
                "spacing_unit": 4,
            },
        },
    },

    "任务管理仪表盘": {
        "app_type": "dashboard",
        "example_prompt": "创建一个任务管理仪表盘，可以查看待办、进行中和已完成的任务，支持按状态筛选",
        "default_schema": {
            "app_id": "tpl_task_dashboard",
            "title": "任务管理",
            "app_type": "dashboard",
            "pages": [
                {
                    "id": "page_dashboard",
                    "name": "任务看板",
                    "route": "/",
                    "components": [
                        {"id": "nav1", "type": "navbar", "props": {"title": "任务管理", "links": []}, "children": [], "actions": []},
                        {"id": "stats", "type": "card", "props": {"title": "概览"}, "children": [
                            {"id": "stat1", "type": "stat-card", "props": {"label": "总任务", "value": "12", "change": "本周 +3"}, "children": [], "actions": []},
                            {"id": "stat2", "type": "stat-card", "props": {"label": "进行中", "value": "5"}, "children": [], "actions": []},
                            {"id": "stat3", "type": "stat-card", "props": {"label": "已完成", "value": "7"}, "children": [], "actions": []},
                        ], "actions": []},
                        {"id": "tbl1", "type": "table", "props": {
                            "columns": ["任务名称", "状态", "优先级", "截止日期"],
                            "rows": [
                                {"任务名称": "完成需求文档", "状态": "进行中", "优先级": "高", "截止日期": "2025-02-01"},
                                {"任务名称": "UI 设计评审", "状态": "待办", "优先级": "中", "截止日期": "2025-02-05"},
                                {"任务名称": "后端 API 开发", "状态": "已完成", "优先级": "高", "截止日期": "2025-01-30"},
                            ],
                        }, "children": [], "actions": []},
                    ],
                }
            ],
        },
    },

    "反馈收集工具": {
        "app_type": "form",
        "example_prompt": "做一个产品反馈收集工具，包含评分（1-5星）、反馈类型选择和详细描述输入",
        "default_schema": {
            "app_id": "tpl_feedback",
            "title": "产品反馈",
            "app_type": "form",
            "pages": [
                {
                    "id": "page_feedback",
                    "name": "反馈",
                    "route": "/",
                    "components": [
                        {"id": "h1", "type": "heading", "props": {"text": "您的反馈很重要"}, "children": [], "actions": []},
                        {"id": "txt1", "type": "text", "props": {"text": "请告诉我们您的使用体验，帮助我们不断改进。"}, "children": [], "actions": []},
                        {"id": "form1", "type": "form", "props": {}, "children": [
                            {"id": "sel_type", "type": "select", "props": {"label": "反馈类型", "name": "type", "form_id": "form1", "options": ["功能建议", "Bug 报告", "体验问题", "其他"]}, "children": [], "actions": []},
                            {"id": "inp_desc", "type": "input", "props": {"label": "详细描述", "name": "description", "placeholder": "请描述您遇到的问题或建议...", "form_id": "form1"}, "children": [], "actions": []},
                            {"id": "btn_submit", "type": "button", "props": {"label": "提交反馈"}, "children": [], "actions": [{"trigger": "click", "type": "submit_form", "payload": {"form_id": "form1"}}]},
                        ], "actions": []},
                    ],
                }
            ],
        },
    },

    "活动介绍页": {
        "app_type": "landing",
        "example_prompt": "做一个活动介绍落地页，展示活动主题、时间地点、亮点特色，底部有报名表单",
        "default_schema": {
            "app_id": "tpl_event_landing",
            "title": "活动介绍",
            "app_type": "landing",
            "pages": [
                {
                    "id": "page_landing",
                    "name": "活动详情",
                    "route": "/",
                    "components": [
                        {"id": "h1", "type": "heading", "props": {"text": "2025 年度产品发布会"}, "children": [], "actions": []},
                        {"id": "txt_date", "type": "text", "props": {"text": "📅 2025年3月15日 · 北京国家会议中心"}, "children": [], "actions": []},
                        {"id": "card_features", "type": "card", "props": {"title": "活动亮点"}, "children": [
                            {"id": "tag1", "type": "tag", "props": {"text": "新品首发"}, "children": [], "actions": []},
                            {"id": "tag2", "type": "tag", "props": {"text": "行业大咖"}, "children": [], "actions": []},
                            {"id": "tag3", "type": "tag", "props": {"text": "现场体验"}, "children": [], "actions": []},
                        ], "actions": []},
                        {"id": "form_signup", "type": "form", "props": {}, "children": [
                            {"id": "inp_name", "type": "input", "props": {"label": "姓名", "name": "name", "placeholder": "您的姓名", "form_id": "form_signup"}, "children": [], "actions": []},
                            {"id": "inp_email", "type": "input", "props": {"label": "邮箱", "name": "email", "type": "email", "placeholder": "your@email.com", "form_id": "form_signup"}, "children": [], "actions": []},
                            {"id": "btn_reg", "type": "button", "props": {"label": "立即报名"}, "children": [], "actions": [{"trigger": "click", "type": "submit_form", "payload": {"form_id": "form_signup"}}]},
                        ], "actions": []},
                    ],
                }
            ],
        },
    },

    "简易CRM": {
        "app_type": "dashboard",
        "example_prompt": "做一个简易 CRM 页面，展示客户列表（姓名、公司、状态、最近联系时间），支持查看客户详情",
        "default_schema": {
            "app_id": "tpl_crm",
            "title": "客户管理",
            "app_type": "dashboard",
            "pages": [
                {
                    "id": "page_crm",
                    "name": "客户列表",
                    "route": "/",
                    "components": [
                        {"id": "nav1", "type": "navbar", "props": {"title": "客户管理 CRM", "links": []}, "children": [], "actions": []},
                        {"id": "h1", "type": "heading", "props": {"text": "客户列表"}, "children": [], "actions": []},
                        {"id": "tbl_clients", "type": "table", "props": {
                            "columns": ["客户名称", "公司", "状态", "最近联系"],
                            "rows": [
                                {"客户名称": "张三", "公司": "科技有限公司", "状态": "潜在客户", "最近联系": "2025-01-15"},
                                {"客户名称": "李四", "公司": "互联网集团", "状态": "成交客户", "最近联系": "2025-01-20"},
                                {"客户名称": "王五", "公司": "制造业股份", "状态": "跟进中", "最近联系": "2025-01-22"},
                            ],
                        }, "children": [], "actions": []},
                    ],
                }
            ],
        },
    },
}


def get_template(name: str) -> dict[str, Any] | None:
    return TEMPLATES.get(name)


def list_templates() -> list[str]:
    return list(TEMPLATES.keys())
