# Nano Atoms — 系统设计文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户浏览器                         │
│  Landing / Auth / Dashboard / Workspace / PublicApp  │
│         Next.js 15 + React 19 + Tailwind CSS         │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (REST + WebSocket)
┌──────────────────▼──────────────────────────────────┐
│                  FastAPI 后端                         │
│  /api/auth  /api/projects  /api/generate  /api/pub   │
│  /ws/projects/:id/generation  (WebSocket)            │
└──────────────────┬──────────────────────────────────┘
          ┌────────┴────────┐
          │                 │
┌─────────▼──────┐ ┌───────▼──────────────────────────┐
│  SQLite DB     │ │  LangGraph 多智能体编排            │
│  (SQLModel)    │ │                                    │
│                │ │  Orchestrator                      │
│  users         │ │    ├── Product Agent               │
│  projects      │ │    ├── Architect Agent             │
│  conversations │ │    ├── UI Builder Agent            │
│  messages      │ │    ├── Code Agent                  │
│  app_versions  │ │    └── QA Agent                    │
│  agent_runs    │ │                                    │
│  published_apps│ │  ← OpenAI 兼容接口（结构化输出）  │
└────────────────┘ └──────────────────────────────────┘
```

## 2. 数据模型 ER 图

```
users
  ├── id (PK)
  ├── email (UNIQUE)
  ├── password_hash
  └── created_at
       │
       ▼ 1:N
projects
  ├── id (PK)
  ├── user_id (FK → users)
  ├── name
  ├── app_type  # form | dashboard | landing | tool
  ├── latest_version_id (FK → app_versions, nullable)
  └── created_at
       │
       ├──────────────────────────┐
       ▼ 1:1                      ▼ 1:N
conversations              app_versions
  ├── id (PK)                ├── id (PK)
  ├── project_id (FK)        ├── project_id (FK)
  ├── mode                   ├── version_no
  └── created_at             ├── prompt_snapshot
       │                     ├── schema_json      # app-schema
       ▼ 1:N                 ├── code_json        # code-bundle
messages                     ├── preview_snapshot
  ├── id (PK)                ├── status
  ├── conversation_id (FK)   └── created_at
  ├── role                        │
  ├── agent_name (nullable)       ├────────────┐
  ├── content                     ▼ 1:N        ▼ 1:N
  └── created_at             agent_runs    published_apps
                               ├── id          ├── id
                               ├── version_id  ├── project_id
                               ├── agent_name  ├── version_id
                               ├── status      ├── slug (UNIQUE)
                               ├── output_sum  ├── is_active
                               ├── started_at  └── created_at
                               └── ended_at
```

## 3. Agent 状态机

### 生成任务状态
```
queued → running → waiting_review → completed
                 ↘ failed
```

### 单个 Agent 状态
```
pending → running → done
                  ↘ error
```

### LangGraph 节点流
```
START
  │
  ▼
product_agent   → prd_json
  │
  ▼
architect_agent → app_schema
  │
  ▼
ui_builder_agent → ui_theme (merge into app_schema)
  │
  ▼
code_agent      → code_bundle
  │
  ▼
qa_agent        → qa_result
  │
  ├── passed=True  → END (version saved, WS notify)
  └── passed=False → code_agent (retry max 1 次)
```

## 4. 生成产物 Schema 定义

### 4.1 AppSchema（app-schema.json）

```typescript
interface AppSchema {
  app_id: string;
  title: string;
  app_type: "form" | "dashboard" | "landing" | "tool";
  pages: Page[];
  navigation?: NavigationItem[];
  data_models?: DataModel[];
}

interface Page {
  id: string;
  name: string;
  route: string;
  components: ComponentNode[];
}

interface ComponentNode {
  id: string;
  type: ComponentType;
  props: Record<string, unknown>;
  children?: ComponentNode[];
  actions?: ActionDef[];
  style?: StyleProps;
}

type ComponentType =
  | "text" | "heading" | "image" | "button"
  | "input" | "select" | "table" | "card"
  | "form" | "modal" | "tag" | "navbar" | "stat-card";

interface ActionDef {
  trigger: "click" | "submit" | "change";
  type: "navigate" | "submit_form" | "open_modal" | "close_modal" | "set_value";
  payload?: Record<string, unknown>;
}
```

### 4.2 UITheme（ui-theme.json）

```typescript
interface UITheme {
  primary_color: string;
  secondary_color: string;
  background_color: string;
  text_color: string;
  font_family: string;
  border_radius: string;
  spacing_unit: number;
}
```

### 4.3 CodeBundle（code-bundle.json）

```typescript
interface CodeBundle {
  form_handlers: FormHandler[];
  data_bindings: DataBinding[];
  initial_state: Record<string, unknown>;
}

interface FormHandler {
  form_id: string;
  fields: string[];
  submit_action: "save_local" | "api_call";
  api_endpoint?: string;
}

interface DataBinding {
  component_id: string;
  data_source: string;
  field_path: string;
}
```

## 5. WebSocket 消息协议

### 服务端 → 客户端

```typescript
// Agent 状态变更
interface AgentStatusMessage {
  type: "agent_status";
  agent: "product" | "architect" | "ui_builder" | "code" | "qa";
  status: "running" | "done" | "error";
  summary?: string;
  timestamp: string;
}

// 生成任务状态变更
interface GenerationStatusMessage {
  type: "generation_status";
  status: "queued" | "running" | "completed" | "failed";
  version_id?: string;
  error?: string;
}
```

## 6. API 接口汇总

| Method | Path | 说明 | 认证 |
|--------|------|------|------|
| POST | /api/auth/register | 注册 | 否 |
| POST | /api/auth/login | 登录，返回 JWT | 否 |
| GET | /api/auth/me | 当前用户信息 | 是 |
| GET | /api/projects | 项目列表 | 是 |
| POST | /api/projects | 创建项目 | 是 |
| GET | /api/projects/:id | 项目详情 | 是 |
| PATCH | /api/projects/:id | 更新项目 | 是 |
| POST | /api/projects/:id/generate | 触发生成 | 是 |
| POST | /api/projects/:id/iterate | 追加迭代 | 是 |
| GET | /api/projects/:id/versions | 版本列表 | 是 |
| GET | /api/versions/:id | 版本详情 | 是 |
| POST | /api/projects/:id/publish | 发布版本 | 是 |
| GET | /api/published/:slug | 获取发布内容 | 否 |
| WS | /ws/projects/:id/generation | 实时状态推送 | 否 |
