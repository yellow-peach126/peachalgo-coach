# Contributing

Thanks for helping improve PeachAlgo Coach（黄桃算法教练）.

## Development setup

```bash
# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## Project layout

| Path | Role |
|------|------|
| `backend/app` | FastAPI API, planner, review, stats |
| `backend/data/problems.json` | Free-problem metadata only (no statements) |
| `frontend/src` | Vue 3 UI |
| `docs/` | Product / contribution docs |
| `scripts/build-exe.ps1` | Windows desktop package |

## Contribution ideas

- More free problem metadata → [docs/contribute-problems.md](docs/contribute-problems.md)
- Planner / spaced-review quality
- UI polish & accessibility
- Import/export, diagnostics, templates
- Tests under `backend/tests`

## Pull requests

1. Fork + branch from `main`
2. Keep changes focused
3. Do not commit secrets, local DB, `node_modules`, `.venv`, or `backend/dist`
4. Describe **what / why / how to test**

## Code of conduct (short)

Be respectful. Assume good intent. No harassment.

## License

By contributing, you agree your contributions are licensed under the MIT License.
