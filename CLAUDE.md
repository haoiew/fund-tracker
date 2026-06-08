# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

基金跟踪器 (Fund Tracker) v3.0 — a cross-platform fund tracking and analysis toolkit. Tracks real-time fund valuations, historical NAV, portfolio management, fund screening (consecutive up/down trends), and multi-fund comparison.

## Project Structure

```
fund-tracker/          # Main application
  backend/             # FastAPI + SQLAlchemy (Python)
  frontend/            # Vue 3 + TypeScript, Web-first with Tauri-ready shell hooks
data-source-test/      # Standalone data source benchmarking tool
```

## Common Commands

### One-click start (Windows)
```bash
fund-tracker/scripts/start.bat   # Launches backend (:8001) + frontend (:5173)
```

### Backend
```bash
cd fund-tracker/backend
pip install -r requirements.txt
python -m app.main               # http://127.0.0.1:8001
# API docs: http://127.0.0.1:8001/docs
```

### Frontend
```bash
cd fund-tracker/frontend
npm install
npm run dev                      # http://localhost:3000 (proxies /api/* -> :8001)
npm run tauri:dev:web            # Tauri-oriented web dev mode
npm run tauri:build:web          # Build frontend assets for future Tauri shell
```

### Testing
```bash
cd fund-tracker/backend && pytest                    # Backend tests
cd fund-tracker/backend && pytest tests/test_fund.py # Run single test file
cd fund-tracker/backend && pytest -m "not slow"      # Skip slow tests
cd fund-tracker/backend && pytest -k "test_name"     # Run tests matching pattern
cd data-source-test && python run_all_tests.py       # Data source comparison
```

### Linting
```bash
cd fund-tracker/frontend && npm run lint         # Run oxlint + eslint sequentially
cd fund-tracker/frontend && npm run type-check   # TypeScript type checking only
cd fund-tracker/frontend && npm run build        # Type check + Vite build
```

## Architecture

### Data Flow

```
Frontend (Vue 3)
  -> API modules (src/api/fund.ts, portfolio.ts)
  -> Axios wrapper (src/api/request.ts, auto-unwraps response.data.data)
  -> Vite proxy (/api/* -> http://127.0.0.1:8001/api/v1/)
  -> FastAPI routes (api/v1/)
  -> Service layer (services/)
  -> DataSourceManager (core/data_source.py) with strategy chain
  -> SQLite + In-memory LRU cache
```

### Backend Architecture (fund-tracker/backend/app/)

- **config.py** — Centralized Settings dataclass, single source of truth for all config
- **core/data_source.py** — DataSourceManager with strategy chain: efinance (primary batch) -> eastmoney_direct (fallback per-fund, with sub-strategies: tiantian, tencent, lsjz, pingzhongdata). QDII funds prefer Tencent API.
- **core/cache.py** — In-memory LRU cache (no Redis dependency)
- **core/scheduler.py** — APScheduler background tasks
- **services/** — Business logic: fund_service (data/screen/compare), history_service (NAV persistence), portfolio_service (CRUD + profit calc)
- **schemas/common.py** — ResponseModel wrapper used by all endpoints

### Frontend Architecture (fund-tracker/frontend/src/)

- **main.ts** — Bootstrap: Pinia, Router, Element Plus, vue-i18n, ECharts (registered globally)
- **stores/dataManager.ts** — Unified reactive state with localStorage persistence for offline resilience
- **stores/fundStore.ts / portfolioStore.ts** — Pinia stores
- **api/request.ts** — Axios instance; note the auto-unwrap interceptor extracts `response.data.data`
- **views/Home/HomeView.vue** — Main dashboard (largest view component)
- **router/index.ts** — 6 routes: Home, Screen, Compare, Portfolio, Settings, About

### Key Design Decisions

- SQLite + in-memory cache — zero infrastructure dependencies (no Docker/Redis/PostgreSQL required for dev)
- Multi-source data fetching with automatic fallback for reliability
- Frontend proxies `/api/*` via Vite dev server; production uses `/api/v1` directly
- Frontend stays Web-first; Tauri integration points are reserved for desktop and future Android packaging

### data-source-test/

Standalone benchmarking project for evaluating data source providers (akshare, efinance, tushare, eastmoney). Each adapter implements `sources/base.py`. Tests cover feasibility, stability, accuracy, timeliness, and batch performance.

## Environment Notes

- Python 3.11+ required
- Node.js ^20.19.0 || >=22.12.0 required
- Frontend env: `.env.development` (VITE_API_BASE_URL=/api), `.env.production` (VITE_API_BASE_URL=/api/v1)
- pytest markers: `slow`, `integration` (see backend/pytest.ini)
- pytest config: `asyncio_mode = auto` for async test support
