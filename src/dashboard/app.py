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
    INTERVAL_LABELS,
    STRATEGY_PRESETS,
    BacktestRequest,
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

    # S42.4 — disable static file caching (dev tool, prevents stale JS/CSS issues)
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response

    @app.middleware("http")
    async def _no_cache_static(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        # S42.4 — cache-bust static assets via mtime query param
        import os

        css_mtime = int(os.path.getmtime(_DIR / "static" / "dashboard.css"))
        js_mtime = int(os.path.getmtime(_DIR / "static" / "dashboard.js"))
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "strategies": STRATEGY_PRESETS,
                "intervals": INTERVAL_LABELS,
                "css_v": css_mtime,
                "js_v": js_mtime,
            },
        )

    @app.get("/api/strategies")
    async def get_strategies() -> dict[str, dict[str, object]]:
        # Return id → {label, type} only (no nested config exposure)
        return {
            sid: {"id": sid, "label": s["label"], "type": s["type"]}
            for sid, s in STRATEGY_PRESETS.items()
        }

    @app.get("/api/strategy/{strategy_id}/info")
    async def get_strategy_info(strategy_id: str) -> dict[str, object]:
        """S42 T5 — preset metadata + supported_combos for frontend gates."""
        preset = STRATEGY_PRESETS.get(strategy_id)
        if preset is None:
            raise HTTPException(status_code=404, detail=f"Unknown strategy: {strategy_id}")
        # supported_combos: list of (symbol, interval) tuples — convert к list[list] для JSON
        sc_raw = preset.get("supported_combos", [])
        sc_serialized: list[list[str]] = [list(combo) for combo in sc_raw]
        return {
            "id": strategy_id,
            "label": preset["label"],
            "type": preset["type"],
            "supported_combos": sc_serialized,
            "locked_symbol": preset.get("locked_symbol"),
            "locked_interval": preset.get("locked_interval"),
        }

    @app.get("/api/intervals")
    async def get_intervals() -> list[dict[str, str]]:
        return [{"id": k, "label": v} for k, v in INTERVAL_LABELS.items()]

    @app.get("/api/data/availability")
    async def get_availability() -> dict[str, dict[str, object]]:
        return list_data_availability()

    @app.post("/api/backtest")
    async def post_backtest(payload: BacktestPayload = Body(...)) -> dict[str, object]:  # noqa: B008
        # S39 T4 — ENFORCE locked dimensions (ADR 0059 anti-snooping)
        preset = STRATEGY_PRESETS.get(payload.strategy_id)
        if preset is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown strategy_id: {payload.strategy_id}",
            )
        locked_symbol = preset.get("locked_symbol")
        locked_interval = preset.get("locked_interval")
        if locked_symbol and payload.symbol != locked_symbol:
            raise HTTPException(
                status_code=422,
                detail=f"Strategy {payload.strategy_id} LOCKED to symbol={locked_symbol}; got {payload.symbol}",
            )
        if locked_interval and payload.interval != locked_interval:
            raise HTTPException(
                status_code=422,
                detail=f"Strategy {payload.strategy_id} LOCKED to interval={locked_interval}; got {payload.interval}",
            )

        # S42 T5 — supported_combos enforcement (multi-combo presets like atr_breakout)
        supported_combos = preset.get("supported_combos")
        if supported_combos:
            combo_key = (payload.symbol, payload.interval)
            # supported_combos may be list[tuple] OR list[list] (after JSON round-trip)
            normalized = [tuple(c) for c in supported_combos]
            if combo_key not in normalized:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Strategy {payload.strategy_id} has no LOCKED params для combo "
                        f"({payload.symbol}, {payload.interval}). "
                        f"supported_combos: {normalized}"
                    ),
                )

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
