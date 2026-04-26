"""Dashboard UI bounded context (Sprint 25 ADR 0039).

NEW Presentation context. Read-only к existing data sources (Parquet OHLCV +
SQLite WAL state). NO execution/risk imports (architectural isolation per
S25 architecture-reviewer verdict).

Optional dependency group `dashboard` (FastAPI + uvicorn + jinja2). Install via
`pip install -e ".[dashboard]"`. Core WFA pipeline (_cmd_wfa) does NOT depend
on these — gracefully fails если dashboard deps not installed.

Launch: `scripts/dashboard.sh` → uvicorn на http://127.0.0.1:8000 + auto-opens
browser.
"""
