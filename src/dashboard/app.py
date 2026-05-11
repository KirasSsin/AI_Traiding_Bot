"""Dashboard FastAPI application — S25 ADR 0039.

Localhost-only (127.0.0.1:8000). NO auth, NO CORS (single-user dev tool).

Endpoints:
  GET  /                       — React SPA (S46 architect C4: FileResponse)
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
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.dashboard.account_service import get_account_balance
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
from src.dashboard.glossary_data import get_glossary
from src.dashboard.strategy_descriptions import get_strategy_description
from src.dashboard.wfa_criterion_explanations import (
    CriterionExplanation,
    get_all_criterion_explanations,
)

_DIR = Path(__file__).resolve().parent

# S46 architect C1+C4 BINDING — обслуживать React build из src/dashboard_react/dist/
_DIST_DIR = _DIR.parent / "dashboard_react" / "dist"


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
    initial_balance: float = Field(default=10000.0, gt=0, le=1_000_000)


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AI Trading Bot — Dashboard",
        description="S25 ADR 0039 — backtest comparison UI (demo-only).",
        version="0.1.0-alpha.25",
    )

    # S46 architect C1 — монтировать React assets из dist/assets/ (content-hashed Vite output)
    if _DIST_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(_DIST_DIR / "assets")), name="assets")

    # S46 architect C4 — FileResponse для React SPA; graceful fallback если build отсутствует
    if _DIST_DIR.exists():

        @app.get("/", response_class=FileResponse)
        async def index_react() -> FileResponse:
            return FileResponse(_DIST_DIR / "index.html")
    else:

        @app.get("/", response_class=HTMLResponse)
        async def index_missing() -> HTMLResponse:
            return HTMLResponse(
                "<h1>React build missing</h1>"
                "<p>Run <code>npm run build</code> в <code>src/dashboard_react/</code></p>",
                status_code=503,
            )

    @app.get("/api/strategies")
    async def get_strategies() -> dict[str, dict[str, object]]:
        # S43 T2 — include description + optgroup (frontend dropdown grouping + description block)
        return {
            sid: {
                "id": sid,
                "label": s["label"],
                "type": s["type"],
                "description": s.get("description", ""),
                "optgroup": s.get("optgroup", ""),
            }
            for sid, s in STRATEGY_PRESETS.items()
        }

    @app.get("/api/strategy/{strategy_id}/info")
    async def get_strategy_info(strategy_id: str) -> dict[str, object]:
        """S42 T5 — preset metadata + supported_combos for frontend gates.
        S43 T2 — added description + optgroup fields для UI block.
        """
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
            "description": preset.get("description", ""),
            "optgroup": preset.get("optgroup", ""),
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
            return run_backtest(req, force=payload.force, initial_balance=payload.initial_balance)
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

    @app.get("/api/strategy_explanation/{preset_id}")
    async def strategy_explanation(preset_id: str) -> dict[str, str]:
        """S47 T15 — RU detailed strategy description for FailAnalysisTab."""
        desc = get_strategy_description(preset_id)
        if desc is None:
            raise HTTPException(status_code=404, detail=f"Unknown preset: {preset_id}")
        return {"preset_id": preset_id, "description_ru": desc}

    @app.get("/api/wfa_criterion_explanations")
    async def wfa_criterion_explanations() -> dict[str, CriterionExplanation]:
        """S47 T15 — RU formula+threshold+impact per WFA criterion (T1-T6 + DSR + MC)."""
        return get_all_criterion_explanations()

    @app.get("/api/glossary")
    async def glossary() -> dict[str, object]:
        """S48 T6 — RU glossary content + per-strategy applicability map (architect C3 BINDING)."""
        return get_glossary()

    @app.get("/api/bybit/balance")
    async def bybit_balance() -> dict[str, Any]:
        """S48 T4 — fetch current Bybit account balance (via account_service wrapper)."""
        return get_account_balance()

    # S47 T7 python-reviewer S46 MEDIUM — cache headers per content type.
    # /assets/* = content-hashed Vite output → immutable forever.
    # index.html / /api/* / SPA catch-all → no-cache (dynamic; references new hashes per build).
    class _CacheControlMiddleware(BaseHTTPMiddleware):
        """Set cache headers per content type."""

        async def dispatch(self, request: Request, call_next: Any) -> Response:
            response: Response = await call_next(request)
            path = request.url.path
            if path.startswith("/assets/"):
                response.headers["Cache-Control"] = "public, immutable, max-age=31536000"
            else:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    app.add_middleware(_CacheControlMiddleware)

    # S47 T6 architect MEDIUM (S46 followup) — SPA catch-all для client-side routing.
    # Mount order: ALL /api/* + /assets/* MUST be registered BEFORE this catch-all.
    # FastAPI matches routes в registration order; catch-all should be last.
    if _DIST_DIR.exists():

        @app.get("/{path:path}", response_class=FileResponse, include_in_schema=False)
        async def spa_fallback(path: str) -> FileResponse:  # noqa: ARG001
            # Любой non-API non-asset path → serve React SPA shell.
            # React Router (если added в future) handles client-side routing.
            return FileResponse(_DIST_DIR / "index.html")

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
