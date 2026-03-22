# Nano Atoms

多智能体驱动的网页应用生成平台。用户输入自然语言需求，系统通过 6 个协作 Agent 完成需求拆解、结构设计、UI 生成、逻辑配置和配图生成，实时预览并支持持续迭代与发布。

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Next.js 15 + React 19 + TypeScript + Tailwind CSS |
| 后端 | FastAPI + Python 3.12 |
| 多智能体 | LangGraph |
| 数据库 | SQLite + SQLModel |
| 认证 | JWT (python-jose) |
| 实时通信 | WebSocket |

## 快速启动

### 1. 后端

```bash
cd backend

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 SECRET_KEY
# 后端可通过 OPENAI_IMAGE_* 接入可选的独立配图模型

# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn app.main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动
npm run dev
```

访问 http://localhost:3000

## 项目结构

```
nano-atoms/
├── docs/
│   └── design.md          # 系统设计文档（架构、数据模型、Schema 定义）
├── frontend/              # Next.js 前端
│   ├── app/               # Next.js App Router 页面
│   ├── components/
│   │   ├── renderer/      # 动态渲染器（Schema → React 组件）
│   │   └── workspace/     # Workspace 专属组件
│   ├── hooks/             # useAuth, useWebSocket
│   ├── stores/            # Zustand 状态管理
│   └── types/             # TypeScript 类型定义
└── backend/               # FastAPI 后端
    └── app/
        ├── agents/        # LangGraph 多智能体（6 个 Agent + Orchestrator）
        ├── api/           # REST API 路由
        ├── core/          # 配置、数据库、安全、模板
        ├── models/        # SQLModel 数据库模型（7张表）
        └── services/      # 生成服务、发布服务
```

## 核心流程

```
用户输入需求
     ↓
POST /api/projects/:id/generate
     ↓
LangGraph 图执行（后台异步）
     ├── Product Agent  → prd_json
     ├── Architect Agent → app_schema
     ├── UI Builder     → ui_theme
     ├── Code Agent     → code_bundle
     ├── Media Agent    → 生成配图资源
     └── QA Agent       → 质量验证
     ↓
WebSocket 推送状态 → 前端 AgentPanel 实时更新
     ↓
版本入库 → 前端 PreviewPanel 动态渲染
```

## 功能列表

### P0（已实现）
- ✅ 注册 / 登录（JWT）
- ✅ 项目创建与管理
- ✅ 多智能体生成（5个 Agent）
- ✅ 生成过程实时展示（WebSocket）
- ✅ 可视化预览（Schema → React 渲染）
- ✅ 二次编辑与迭代
- ✅ 数据持久化（7张表）
- ✅ 版本管理
- ✅ 发布为公开链接

### P1（已实现）
- ✅ 模板系统（5个预置模板）
- ✅ Race Lite（并行生成两方案）
- ✅ 历史版本切换

## 环境变量

```env
# 后端 .env
DATABASE_URL=sqlite:///./nano_atoms.db
SECRET_KEY=your-32-char-secret-key
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_IMAGE_API_KEY=
OPENAI_IMAGE_BASE_URL=
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_IMAGE_ENABLED=true
OPENAI_IMAGE_MAX_ASSETS=4
FRONTEND_URL=http://localhost:3000

# 前端 .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

后端可选使用 `OPENAI_IMAGE_API_KEY`、`OPENAI_IMAGE_BASE_URL` 和 `OPENAI_IMAGE_MODEL` 走独立配图链路。未单独配置时，后端会默认复用主 `OPENAI_*` 配置；如果图片接口不可用，会自动跳过配图，不影响主生成流程。
