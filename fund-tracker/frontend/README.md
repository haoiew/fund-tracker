# Fund Tracker Frontend

Vue 3 + TypeScript + Element Plus frontend for Fund Tracker. The Vite dev server is pinned to `http://localhost:3000` by `vite.config.ts` and proxies `/api/*` to `http://127.0.0.1:8001/api/v1/*`.

## Commands

```bash
npm install
npm run dev          # http://localhost:3000
npm run type-check
npm run build        # type-check + Vite production build
npm run lint
npm run tauri:dev:web
npm run tauri:build:web
```

## Runtime Notes

- Use `scripts/start.bat` from the repository root on Windows when you want the canonical local stack. It clears ports `8001`, `3000`, and `5173`, then starts backend `8001` and frontend `3000`.
- Avoid using alternate frontend origins such as `127.0.0.1:5173` for normal testing. Browser `localStorage` is origin-scoped, so different frontend URLs can create separate caches and make data state hard to reason about.
- Development API base defaults to `/api`; the Vite proxy rewrites it to `/api/v1` on the backend.
- Tauri-specific web mode uses `--mode tauri`, keeps the same Vue application, and can switch API base through `VITE_TAURI_API_BASE_URL`.

## Key Areas

- `src/api/request.ts` wraps Axios and unwraps `ResponseModel.data`.
- `src/stores/dataManager.ts` coordinates local cache and refresh flows.
- `src/views/Home/HomeView.vue` renders realtime fund tracking and data-source comparison.
- `src/views/Portfolio/PortfolioView.vue` handles holdings, AI screenshot recognition, import preview, and confirm import.
- `src/views/Settings/SettingsView.vue` stores AI provider configs and can test both text and image-input connectivity.
