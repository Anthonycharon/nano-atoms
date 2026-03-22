# Repository Guidelines

## Project Structure & Module Organization
`frontend/` contains the Next.js app. Use `frontend/app/` for App Router pages, `frontend/components/` for shared UI and renderer code, `frontend/hooks/` for React hooks, `frontend/stores/` for Zustand state, and `frontend/types/` for shared TypeScript types. `backend/` contains the FastAPI service: `backend/app/api/` for routers, `agents/` for LangGraph agents, `services/` for orchestration, `models/` for SQLModel tables, `schemas/` for request/response models, and `core/` for config, database, and security utilities. Keep design notes in `docs/`.

## Build, Test, and Development Commands
Run backend and frontend separately; there is no root task runner.

- `python -m pip install -r backend/requirements.txt`: install backend dependencies.
- `uvicorn app.main:app --reload --port 8000` (from `backend/`): start the API locally.
- `npm install` (from `frontend/`): install frontend dependencies.
- `npm run dev` (from `frontend/`): start the Next.js dev server on port 3000.
- `npm run build` and `npm run start` (from `frontend/`): build and serve the production frontend.

## Coding Style & Naming Conventions
Python code uses 4-space indentation, type hints, and snake_case module names. Keep FastAPI routers thin and move reusable logic into `services/` or `agents/`. TypeScript runs in strict mode. Follow the existing frontend style: semicolons, double quotes, PascalCase component files, camelCase variables/functions, and the `@/*` import alias from `frontend/tsconfig.json`. Route files should remain under `frontend/app/**/page.tsx`.

## Testing Guidelines
No automated test runner is configured at the repository root today, and there is no enforced coverage threshold yet. For backend work, add `pytest` tests under `backend/tests/` when introducing non-trivial logic. For frontend work, prefer `*.test.ts` or `*.test.tsx` files under `frontend/` once a runner is added. Before opening a PR, at minimum run `npm run build`, start the API, and smoke-test `/health`, auth flows, dashboard, and workspace pages.

## Commit & Pull Request Guidelines
Available git history is minimal, so use short imperative commit subjects and add scope prefixes when helpful, for example `backend: validate publish payload` or `frontend: refine workspace renderer`. PRs should include a clear summary, linked issue or requirement, manual verification steps, and screenshots for UI changes. Call out any `.env` or API contract changes explicitly.

## Configuration Notes
Copy `backend/.env.example` to `backend/.env` before running the API. Set `OPENAI_API_KEY`, `SECRET_KEY`, and `FRONTEND_URL` locally. If you modify the Next.js app, read `frontend/AGENTS.md` first; it contains version-specific guidance for this frontend.
