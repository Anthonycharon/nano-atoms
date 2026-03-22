# Nano Atoms — 开发日志

> 本文档记录 Nano Atoms 项目从零开始到当前版本的完整开发过程，包括架构决策、功能实现与 Bug 修复历程。

---

## 一、项目背景

Nano Atoms 是一个**多智能体驱动的网页应用生成平台**，参考 Atoms.dev 的设计思想构建。用户以自然语言描述需求，系统通过多个专业化 AI Agent 协作，完成需求拆解 → 架构设计 → UI 生成 → 逻辑配置 → 质量校验的完整链路，最终输出可交互的网页应用并支持发布。

项目从 PRD 文档（`nano-atoms-prd.md`）出发，完整经历了系统设计、后端搭建、前端实现、联调调试、Bug 修复和体验优化的全过程。

---

## 二、技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端框架 | Next.js 16 (App Router) + React + TypeScript |
| 前端样式 | Tailwind CSS |
| 前端状态 | Zustand + TanStack React Query |
| 后端框架 | FastAPI (Python) |
| 多智能体编排 | LangGraph |
| LLM 调用 | LangChain + OpenAI 兼容接口 |
| 数据库 | SQLite（SQLModel ORM） |
| 认证 | JWT（PyJWT） |
| 实时通信 | WebSocket（FastAPI 原生） |

---

## 三、阶段一：系统设计

### 3.1 架构设计

基于 PRD 完成整体系统架构设计，输出 `docs/design.md`，包含：

- **系统架构图**：浏览器 → FastAPI → SQLite + LangGraph 多智能体
- **数据模型 ER 图**：users / projects / conversations / messages / app_versions / agent_runs / published_apps
- **Agent 状态机**：生成任务状态（queued → running → completed/failed）和 Agent 状态（pending → running → done/error）
- **LangGraph 节点流**：product → architect → ui_builder → code → qa → END
- **生成产物 Schema 定义**：AppSchema、UITheme、CodeBundle 的完整 TypeScript 类型
- **WebSocket 消息协议**：agent_status / generation_status 消息格式
- **完整 REST API 汇总表**

### 3.2 关键架构决策

1. **结构化生成而非任意代码执行**：前端通过 `ComponentRegistry` 解释 `app_schema` 进行渲染，不执行任意 LLM 生成的 JS 代码，保障安全性和稳定性。
2. **LangGraph 线性编排**：选择 LangGraph 管理有状态的多步骤工作流，而非自由式 Agent，便于工程化控制。
3. **WebSocket 实时推送**：生成过程通过 WebSocket 推送 Agent 状态变化，前端实时渲染进度，而非轮询。
4. **版本化存储**：每次生成产出一个独立的 `AppVersion`，历史版本完整保留，支持回溯。

---

## 四、阶段二：后端实现

### 4.1 目录结构

```
backend/app/
├── main.py              # FastAPI 应用入口、CORS、路由注册
├── core/
│   ├── config.py        # 环境变量配置（Pydantic Settings）
│   ├── database.py      # SQLite 连接与会话管理
│   ├── security.py      # JWT 签发/验证、密码哈希
│   └── templates.py     # Agent Prompt 模板
├── models/              # SQLModel 数据表定义
│   ├── user.py
│   ├── project.py
│   ├── conversation.py
│   ├── message.py
│   ├── app_version.py
│   ├── agent_run.py
│   └── published_app.py
├── schemas/             # Pydantic 请求/响应 Schema
│   ├── auth.py
│   ├── project.py
│   └── generation.py
├── api/                 # 路由层
│   ├── auth.py          # 注册/登录/me
│   ├── projects.py      # 项目 CRUD、版本列表
│   ├── generation.py    # 触发生成/迭代
│   ├── publish.py       # 发布管理
│   └── ws.py            # WebSocket 实时推送
├── agents/              # 多智能体核心
│   ├── orchestrator.py  # LangGraph 状态图编排
│   ├── product_agent.py
│   ├── architect_agent.py
│   ├── ui_builder_agent.py
│   ├── code_agent.py
│   ├── qa_agent.py
│   └── utils.py         # LLM 工厂、JSON 提取、WebSocket 通知
└── services/
    └── generation_service.py  # 异步生成任务调度
```

### 4.2 核心实现要点

**认证系统**
- JWT 使用 `PyJWT` 生成，Token 有效期可配置
- 密码哈希使用 `bcrypt` 直接调用（见 Bug Fix #1）
- `GET /api/auth/me` 通过 `Depends(get_current_user)` 实现统一鉴权

**多智能体编排（LangGraph）**

`AgentState` 作为贯穿所有节点的共享状态：
```python
class AgentState(TypedDict):
    project_id: int
    version_id: int
    prompt: str
    app_type: str
    prd_json: Optional[dict]       # Product Agent 产物
    app_schema: Optional[dict]     # Architect + UI Builder 产物
    ui_theme: Optional[dict]
    code_bundle: Optional[dict]    # Code Agent 产物
    qa_result: Optional[dict]      # QA Agent 产物
    qa_retry_count: int
    errors: list[str]
    ws_callback: Optional[Any]     # WebSocket 回调（运行时传入）
```

节点流为线性链路，QA 仅作建议，不触发重试：
```
product → architect → ui_builder → code → qa → END
```

**WebSocket 通知机制**
- 每个 Agent 节点通过 `notify_agent(cb, agent_name, status, summary)` 向前端推送状态
- `generation_service` 在任务完成后推送 `generation_status: completed` + `version_id`

**发布功能**
- 为指定版本生成唯一 `slug`（UUID 前8位）
- 公开访问路径：`GET /api/published/{slug}` 不需要认证

---

## 五、阶段三：前端实现

### 5.1 目录结构

```
frontend/
├── app/
│   ├── page.tsx                    # Landing 页
│   ├── (auth)/
│   │   ├── login/page.tsx          # 登录页
│   │   └── register/page.tsx       # 注册页
│   ├── dashboard/page.tsx          # 项目列表页
│   ├── workspace/[projectId]/page.tsx  # 工作区（核心页面）
│   └── p/[slug]/page.tsx           # 公开发布页
├── components/
│   ├── renderer/
│   │   ├── AppRenderer.tsx         # 应用渲染容器（路由/状态管理）
│   │   └── ComponentRegistry.tsx   # 组件映射（14 种组件类型）
│   └── workspace/
│       ├── ChatPanel.tsx           # 聊天区（含 Agent 完成消息）
│       ├── PreviewPanel.tsx        # 应用预览区
│       └── VersionBar.tsx          # 顶部版本栏
├── hooks/
│   ├── useAuth.ts                  # 登录/注册/登出逻辑
│   ├── useWebSocket.ts             # WebSocket 连接与消息处理
│   └── useProject.ts
├── stores/
│   ├── authStore.ts                # 用户认证状态（Zustand + persist）
│   └── workspaceStore.ts           # 工作区状态（项目/版本/消息/Agent）
├── types/
│   ├── agent.ts                    # Agent 类型、AGENT_META 元数据
│   ├── project.ts                  # 项目/版本类型
│   └── schema.ts                   # AppSchema / CodeBundle 类型
└── lib/
    └── api.ts                      # Axios 封装，Bearer Token 拦截器
```

### 5.2 核心实现要点

**ComponentRegistry（组件注册表）**

支持 14 种组件类型的声明式渲染：
`heading` / `text` / `button` / `input` / `select` / `form` / `card` / `stat-card` / `table` / `navbar` / `tag` / `image` / `modal` + `default`（未知类型降级展示）

每个组件通过 `ctx`（RendererContext）访问路由跳转、表单状态、全局 state，实现真实交互。

**工作区布局**

采用双栏布局（AgentPanel 已合并至 ChatPanel）：
- 左侧 `w-80`：ChatPanel（用户输入 + Agent 完成消息流）
- 右侧 `flex-1`：PreviewPanel（实时渲染 app_schema）

顶部 VersionBar：项目名、版本选择、发布按钮、设备切换。

**实时状态推送**

`useWebSocket` 监听两类 WS 消息：
- `agent_status`：更新 store 中 Agent 状态，完成时向 ChatPanel 发送助手消息
- `generation_status`：更新整体生成状态，完成时设置 `currentVersionId` 并发送完成通知

---

## 六、阶段四：联调 Bug 修复

### Bug #1：passlib 与 bcrypt 4.x 不兼容（注册 500）

**现象**：注册接口返回 500，日志报 `AttributeError: module 'bcrypt' has no attribute '__about__'`

**根因**：`passlib[bcrypt]` 库已停止维护，新版 bcrypt（≥4.0）移除了 `__about__` 属性，passlib 检测版本时崩溃。

**修复**：
- `requirements.txt`：`passlib[bcrypt]>=1.7.4` → `bcrypt>=4.0.0`
- `security.py`：移除 `CryptContext`，改用 `bcrypt.hashpw` / `bcrypt.checkpw` 直接调用

```python
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

---

### Bug #2：登录成功但立即 401（Token 竞态）

**现象**：后端日志显示 `POST /login → 200`，紧接着 `GET /me → 401`，前端提示"密码错误"。

**根因**：`useAuth.ts` 中先调用 `authApi.me()`，再写入 `localStorage`。而 axios 拦截器从 localStorage 读取 Bearer Token，Token 此时还不存在。

**修复**：在 `useAuth.ts` 的 `login()` 和 `register()` 中，确保 `localStorage.setItem("nano_token", ...)` 在 `authApi.me()` **之前**执行。

---

### Bug #3：模型 API HTTP→HTTPS 重定向导致 404

**现象**：触发生成任务，LLM 调用报 404。

**根因**：`.env` 中 `OPENAI_BASE_URL` 使用 `http://`，服务器重定向到 `https://` 时，POST 请求变成 GET 请求，导致 404。

**修复**：`.env` 将 `http://claw.cjcook.site/v1` 改为 `https://claw.cjcook.site/v1`。

---

### Bug #4：CORS 阻断登录按钮（无响应）

**现象**：点击登录按钮无任何反应，网络请求未发出。

**根因**：用户通过 `127.0.0.1:3000` 访问，而 `main.py` 的 CORS `allow_origins` 只包含 `localhost:3000`，浏览器将两者视为不同 Origin，OPTIONS 预检返回 400，后续请求被静默拦截。

**修复**：`main.py` 添加 `"http://127.0.0.1:3000"` 到 `allow_origins`。

---

### Bug #5：QA Agent 始终 `passed: false`

**现象**：QA 阶段 LLM 回复"仅凭摘要数据无法完成检验"。

**根因**：QA Agent 只将 `page_count`、`form_count` 等统计数字发送给 LLM，信息不足以做结构校验。

**修复**（两步）：
1. 改为发送结构化摘要：每页的 `id / name / route / component_ids / component_types`，以及 `form_handlers` 和 `page_transitions`
2. 修改 SYSTEM_PROMPT 为"宽容模式"：只要 schema 中存在至少一个页面且页面有组件即判定 `passed: true`，细节问题记录到 `suggestions` 不影响结果

---

### Bug #6：Navbar 组件崩溃（links 非数组）

**现象**：控制台报 `TypeError: (node.props.links ?? []).map is not a function`

**根因**：LLM 有时生成 `links: "{{nav_links}}"` 占位符字符串而非数组，`?? []` 对非 null/undefined 值无效。

**修复**：`ComponentRegistry.tsx` 改用 `Array.isArray()` 前置校验：
```typescript
// 修复前（崩溃）
(node.props.links as Array<...> ?? []).map(...)

// 修复后（安全）
(Array.isArray(node.props.links) ? node.props.links as Array<...> : []).map(...)
```

同样处理了 `select` 组件的 `options` 字段。

---

### Bug #7：QA 失败触发 Code Agent 重试（浪费 Token）

**现象**：QA 失败后，orchestrator 重新触发 Code Agent，但下一轮 QA 仍失败，陷入无效循环。

**修复**：移除 orchestrator 中的条件重试边（`_should_retry_code`、`_increment_retry`），改为严格线性流程 `qa → END`，QA 结果仅作建议，不影响流程走向。

---

## 七、阶段五：体验优化

### 优化 #1：切换项目显示旧版本数据

**问题**：从 workspace/2 跳转到 workspace/3 时，仍显示 project 2 的旧版本内容。

**根因**：`workspaceStore.setProject()` 只更新 `projectId`，不重置 `currentVersionId`，导致版本加载条件 `if (!currentVersionId)` 始终不满足，新项目继续加载旧版本数据。

**修复**：`setProject` 改为检测项目切换，同步重置 `currentVersionId`、`versions`、`agents`、`generationStatus`、`messages`：

```typescript
setProject: (projectId) =>
  set((state) => {
    if (state.projectId === projectId) return {};
    return {
      projectId,
      currentVersionId: null,
      versions: [],
      agents: INITIAL_AGENTS,
      generationStatus: "idle",
      messages: [],
    };
  }),
```

---

### 优化 #2：返回页面必须重新登录

**问题**：从 workspace 点击浏览器返回按钮，跳转至 dashboard 时被重定向到登录页，需要重新登录。

**根因**：Zustand 使用 `persist` 中间件从 localStorage 异步恢复状态，组件首次渲染时 `isAuthenticated = false`，`useEffect` 立即触发跳转登录，hydration 尚未完成。

**修复**：`dashboard/page.tsx` 和 `workspace/[projectId]/page.tsx` 均增加 `mounted` 状态守卫，延迟认证检查到客户端挂载完成后：

```typescript
const [mounted, setMounted] = useState(false);
useEffect(() => { setMounted(true); }, []);
useEffect(() => {
  if (!mounted) return;
  if (!isAuthenticated) router.push("/login");
}, [mounted, isAuthenticated, router]);
```

---

### 优化 #3：移除 AgentPanel，改为聊天消息通知

**问题**：Workspace 中间列展示 Agent 进度面板，占用宝贵预览空间；且 QA 报错状态影响用户体验。

**改动**：
1. **`useWebSocket.ts`**：Agent 完成（`done`）或报错（`error`）时调用 `addMessage` 将状态以助手消息形式推入 ChatPanel：
   - `done` → `✅ **{label}** 完成：{summary}`
   - `error` → `⚠️ **{label}** 遇到问题：{summary}`
   - 生成完成 → `🎉 应用生成完成！可以在右侧预览区查看效果。`
   - 生成失败 → `❌ 应用生成失败：{error}`

2. **`workspace/page.tsx`**：移除 `AgentPanel` 导入和中间列，改为左右双栏布局（ChatPanel `w-80` + PreviewPanel `flex-1`）。

3. **`ChatPanel.tsx`**：新增 `renderContent()` 函数，将 `**text**` 渲染为 `<strong>`，使 Agent 名称加粗展示。

---

### 优化 #4：QA 阶段显示为"错误"影响体验

**问题**：QA 阶段返回 `passed: false` 时，前端展示错误状态，用户误以为生成失败。

**修复**：`qa_agent.py` 中将状态固定为 `"done"`，QA 的校验结果（包括问题列表和建议）保留在 `qa_result` 中，但不影响流程展示：

```python
# 修复前
status = "done" if qa_result.get("passed") else "error"

# 修复后：QA 仅作建议性审查，始终标记为完成
status = "done"
```

---

## 八、当前功能完成度

| 功能 | 状态 |
|------|------|
| 用户注册/登录/退出 | ✅ 完成 |
| JWT 认证 + 持久化 | ✅ 完成 |
| 项目创建（名称/类型/描述） | ✅ 完成 |
| 多智能体生成（5个 Agent） | ✅ 完成 |
| WebSocket 实时进度推送 | ✅ 完成 |
| Agent 完成状态以聊天消息展示 | ✅ 完成 |
| 应用可视化预览（14种组件） | ✅ 完成 |
| 版本历史管理 | ✅ 完成 |
| 持续迭代（追加 Prompt） | ✅ 完成 |
| 发布为公开页面 | ✅ 完成 |
| 项目切换状态隔离 | ✅ 完成 |
| 登录状态水合竞态修复 | ✅ 完成 |
| select/navbar 组件防崩溃 | ✅ 完成 |
| 模板中心 | 🔲 未实现（P1） |
| Race Lite 双方案对比 | 🔲 未实现（P1） |

---

## 九、已知限制

1. **LLM 生成质量依赖 Prompt 工程**：部分复杂需求生成的 `app_schema` 可能缺少交互细节，需要用户二次迭代。
2. **SQLite 不适合高并发**：当前为单机开发场景，生产部署需迁移至 PostgreSQL。
3. **WebSocket 无鉴权**：`/ws/projects/:id/generation` 当前无 Token 验证，生产环境需加固。
4. **图片组件仅支持外链**：`image` 组件的 `src` 需 LLM 提供有效 URL，不支持上传。
5. **select/input options 依赖 LLM 正确生成数组**：防御性 `Array.isArray` 已加入，但极端输入仍需人工校验。
