"""Dashboard FastAPI application — S25 ADR 0039.

Localhost-only (127.0.0.1:8000). NO auth, NO CORS (single-user dev tool).

Endpoints:
  GET  /                       — static HTML dashboard
  GET  /api/strategies          — strategy presets list
  GET  /api/intervals           — supported timeframes
  GET  /api/data/availability   — per-symbol+interval data availability
  POST /api/backtest            — run WFA на (strategy, symbol, interval, dates)
  GET  /api/runs                — list cached previous runs
  GET  /api/runs/{run_id}       — fetch specific run

Launch: scripts/dashboard.sh OR `python -m src.dashboard.app`.
"""
from __future__ import annotations

import webbrowser
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from src.dashboard.backtest_runner import (
    BacktestRequest,
    INTERVAL_LABELS,
    STRATEGY_PRESETS,
    get_documentation,
    get_run,
    list_data_availability,
    list_runs,
    run_backtest,
)


_DIR = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_DIR / "templates"))


class BacktestPayload(BaseModel):
    """Module-level model — FastAPI resolves к request Body automatically.

    NOTE: Если defined inside create_app() closure → FastAPI 0.136 treats как
    query parameter (422 "missing field"). Must be module-level.
    """
    strategy_id: str
    symbol: str
    interval: str
    start: str
    end: str
    force: bool = False


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AI Trading Bot — Dashboard",
        description="S25 ADR 0039 — backtest comparison UI (demo-only).",
        version="0.1.0-alpha.25",
    )

    app.mount("/static", StaticFiles(directory=str(_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return _TEMPLATES.TemplateResponse(
            request=request, name="index.html", context={
                "strategies": STRATEGY_PRESETS,
                "intervals": INTERVAL_LABELS,
            },
        )

    @app.get("/api/strategies")
    async def get_strategies() -> dict[str, dict[str, object]]:
        # Return id → {label, type} only (no nested config exposure)
        return {
            sid: {"id": sid, "label": s["label"], "type": s["type"]}
            for sid, s in STRATEGY_PRESETS.items()
        }

    @app.get("/api/intervals")
    async def get_intervals() -> list[dict[str, str]]:
        return [{"id": k, "label": v} for k, v in INTERVAL_LABELS.items()]

    @app.get("/api/data/availability")
    async def get_availability() -> dict[str, dict[str, object]]:
        return list_data_availability()

    @app.post("/api/backtest")
    async def post_backtest(payload: BacktestPayload = Body(...)) -> dict[str, object]:
        try:
            req = BacktestRequest(
                strategy_id=payload.strategy_id,
                symbol=payload.symbol,
                interval=payload.interval,
                start=payload.start,
                end=payload.end,
            )
            return run_backtest(req, force=payload.force)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    @app.get("/api/runs")
    async def get_runs() -> list[dict[str, object]]:
        return list_runs()

    @app.get("/api/runs/{run_id}")
    async def get_single_run(run_id: str) -> dict[str, object]:
        result = get_run(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return result

    @app.get("/api/docs")
    async def get_docs() -> dict[str, object]:
        """S26: structured documentation для UI Documentation tab.

        Returns indicators / multipliers / strategies / methodology lists.
        """
        return get_documentation()

    return app


app = create_app()


def main() -> None:
    """Entry-point: start uvicorn + open browser."""
    import uvicorn

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}/"
    print(f"Dashboard starting at {url}")
    print("Press Ctrl+C к stop")

    # Open browser в отдельном thread chain (delayed чтобы uvicorn успел bind)
    def _open() -> None:
        import time
        time.sleep(1.5)
        webbrowser.open(url)

    import threading
    threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
