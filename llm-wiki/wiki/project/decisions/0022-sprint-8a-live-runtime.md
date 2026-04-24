---
title: "0022. Sprint 8a — Live Runtime: RuntimeManager, REST bar poller, KILL_SWITCH, threading lock policy"
type: decision
status: accepted
created: 2026-04-24
updated: 2026-04-24
sources:
  - wiki/project/decisions/0021-sprint-7-resilience.md
  - wiki/project/decisions/0020-sprint-6-execution-spot-oco-emulation.md
  - wiki/project/components/ws-private-consumer.md
  - wiki/project/components/execution-state-machine.md
  - wiki/project/components/reconciler.md
tags: [execution, runtime, orchestration, kill-switch, threading, bar-poller, sprint-8a]
---

# 0022. Sprint 8a — Live Runtime: RuntimeManager, REST bar poller, KILL_SWITCH, threading lock policy

**Status:** accepted
**Date:** 2026-04-24
**Extends:** [[0021-sprint-7-resilience]]
**Closes deferral:** ADR 0021 line 364 (external kill-switch signal → KILL_SWITCH event).

## Context

S7 (ADR 0021) закрыл три resilience gap'а (bootstrap reconcile, WS-reconnect, halt persistence) и оставил **passive WS consumer** (`BybitPrivateWSConsumer`) без driver loop. Bot НЕ запускается end-to-end после S7. Coordinator/Reconciler/FSM работают только в unit-test fixtures.

S8 разбит на **два независимых спринта**:

- **S8a (этот ADR)** — **live runtime**: bring-up процесса, REST bar poller, KILL_SWITCH wiring, threading concurrency model, удаление legacy orphans (`src/controller.py`, `main.py`). Цель: `python -m src run` стартует и торгует на Demo Mainnet.
- **S8b (отдельный ADR позднее)** — Analytics per-fill table + execution topic subscription + WS+REST epsilon-halt consistency check. Зависит от S8a merge.

Split rationale: S8a — orchestration без новых analytical/observability surfaces; S8b — analytical reads на готовом runtime. Один спринт per подсистема (B1 принцип из ADR 0021).

**Trader-expert verdict applied:** brainstorm round 1 (10 CONFIRM / 7 REVISE / 1 DEFER) + round 2 single-item (U1 REVISE).

## Goals & non-goals

**Goals (S8a scope):**

- G1 — `RuntimeManager` class owns process lifecycle: bootstrap → start WS consumer → start bar poller → run loop → shutdown.
- G2 — REST `kline` bar poller (5s cadence), feeds `Strategy.on_bar` → `Coordinator.start_bracket` sequentially. Catch-up reads bars без signal generation (no look-ahead).
- G3 — KILL_SWITCH wiring через **sentinel-file CLI** (`python -m src kill` writes `.kill_switch`; main loop polls each tick → `halt_reason=KILL_SWITCH_REQUESTED`).
- G4 — Threading lock policy на Coordinator + Reconciler (mandatory Task 0). Защищает от pybit thread × main thread race.
- G5 — 3 new reason codes: `43=HALT_RUNTIME_CRASH`, `44=HALT_BAR_POLL_STALL`, `45=KILL_SWITCH_REQUESTED` (42 → 45 total).
- G6 — Entry-point `python -m src` (`src/__main__.py` + argparse subcommands `run` / `backfill` / `reconcile-only` / `kill`).
- G7 — Удалить orphan files: `src/controller.py` (broken since S2), `main.py` (imports broken `src.controller`).
- G8 — Integration test (Demo Mainnet, opt-in `RUN_DEMO=1`): full bring-up → one bar tick → graceful shutdown.

**Non-goals (откладываем → S8b+):**

- WS+REST wallet epsilon-halt consistency check (Q8 verdict: REST canonical per ADR 0020 sub-decision 4 — halting on REST≠WS inverts hierarchy). S8b если потребуется.
- `execution` topic subscription + per-fill Analytics table → S8b.
- Multi-bracket / multi-symbol concurrency → S9+.
- Async/await migration на event loop → S9+ (обоснование: текущий код sync; threading достаточно для 2-3 thread workload v0.1).
- Risk-dashboard override hook (внешний REST endpoint) → v0.2.
- Systemd/launchd service unit → ops concern, отдельный артефакт после tag.

## Sub-decisions

### 1. Concurrency model — sync + threading (Q1 CONFIRM, CC1 REVISE добавляет lock policy)

**Что:** runtime использует **2 threads**:
1. **Main thread** — RuntimeManager loop: bar poller (REST kline @ 5s) + `check_alive` inline + sentinel-file poll. Sequential within tick: poll → check_alive → check_kill → maybe-bar-tick.
2. **pybit thread** (already exists из S7 ws_private consumer) — WS callbacks `_on_order_raw` / `_on_wallet_raw` → `coordinator.on_order_event` / `reconciler.on_wallet_event`.

**Lock policy (mandatory Task 0):**

```python
# src/execution/coordinator.py
class Coordinator:
    def __init__(self, ...):
        self._lock = threading.RLock()  # reentrant: bootstrap may call sub-methods
    
    def bootstrap(self): 
        with self._lock: ...
    def start_bracket(self): 
        with self._lock: ...
    def on_order_event(self, evt): 
        with self._lock: ...
    def on_ws_reconnect(self): 
        with self._lock: ...
    def arm_oco(self): 
        with self._lock: ...
    def flatten(self): 
        with self._lock: ...
```

```python
# src/execution/reconciler.py
class Reconciler:
    def __init__(self, ...):
        self._lock = threading.Lock()  # non-reentrant: paths не вкладываются
    
    def on_wallet_event(self, evt): 
        with self._lock: ...
    def reconcile(self, local, expected_state=None): 
        with self._lock: ...
```

**Почему:** Coordinator FSM transitions трогают same row (`execution_state` SQLite). pybit thread `on_order_event` + main thread `start_bracket`/`flatten` могут race на `_transition` → silent FSM corruption. RLock на Coordinator (reentrant — `bootstrap` зовёт `on_ws_reconnect` который может trigger `_transition`). Reconciler — не reentrant: `on_wallet_event` и `reconcile` не вкладываются.

**Не используется** `asyncio` lock — код sync. Не используется per-method locking без shared state — все 6 методов трогают `_repo` row. Coarse-grained lock приемлем для v0.1 throughput (1H bars + 5s polls).

**Trader-expert annotation:** "zero locks today" = open race door. Без Task 0 любой ENTRY_FILLED event одновременно с `start_bracket` retry = corruption.

### 2. REST bar poller (Q2 CONFIRM)

**Что:** main thread каждые 5 секунд:
1. `bybit.get_kline(symbol="BTCUSDT", interval="60", limit=2)` — последние 2 бара.
2. Если последний closed bar timestamp > previously-seen → emit `on_bar(bar)`.
3. Dedup по `bar_close_ts` (in-memory `_last_bar_ts` field).

**Почему REST а не WS kline:** WS kline streams **partial** bar updates (open bar). Для close-on-close signal (look-ahead invariant) нужны только closed bars. REST дёшев (1 req/5s = 720 req/час, вписывается в Bybit rate limit 600 req/min с большим запасом). WS добавил бы async loop без выигрыша в latency на 1H timeframe.

**Catch-up на startup (Q15 CONFIRM):** RuntimeManager после `bootstrap` читает kline за последние N bars (warmup для indicator state) **без** `on_signal` callback. Только заполняет EMA/ADX/RSI/ATR seed. Первый signal — на закрытии следующего нового bar после startup. Защита от look-ahead на исторических данных (повторное trade events на bars из прошлого).

### 3. `runtime_bar_poll_stall_threshold = 24` (U1 REVISE: 12 → 24)

**Что:** при N consecutive REST poll failures (5s cadence × 24 = 120s) → emit `HALT_BAR_POLL_STALL`, set `halt_reason`, остановить bar tick generation. Position safety НЕ затрагивается — OCO bracket exchange-side, WS consumer routes order events независимо.

```python
# src/platform/config.py
runtime_bar_poll_stall_threshold: int = 24  # 24 × 5s = 120s
# validator: 6 ≤ N ≤ 720  (30s floor — false-halt floor; 1 bar ceiling — meaningless above)
```

**Почему 24, не 12:** trader-expert round 2 verdict — bar-poller stall ≠ position-safety event. OCO bracket exchange-side; WS consumer routes order events независимо. Stall degradates только **new signal generation**. False-halt cost (manual L3 reset) dominates → 24 better balances. 120s = 3.3% от 3600s bar period — survives common Bybit REST transients (10-90s clusters), still halts well before stall could span full bar close.

**Documented degradation (mid-bar fill):** stall starting > 30 min before close может вызвать mid-bar fill вместо open fill. Slippage, не correctness violation. Monitored via structlog `poll_stall_duration_seconds` event.

**Halt class annotation:** `HALT_BAR_POLL_STALL` — **signal-pipeline halt class**, not execution-safety. Runbook должен это отразить. Если в S8b/S9 добавим WS consumer health check — его threshold должен быть **tighter** (~3 ticks at 15s) потому что WS failure = position-safety event.

### 4. `check_alive` INLINE в main thread (Q6 REVISE)

**Что:** `BybitPrivateWSConsumer.check_alive(max_silence_seconds=30.0)` вызывается **внутри** main bar-poll loop (каждый tick), НЕ из отдельного worker thread.

```python
# src/runtime/manager.py
def _tick(self):
    self._maybe_kill_switch()
    if not self._ws_consumer.check_alive(max_silence_seconds=30.0):
        # check_alive itself triggers on_disconnect → coordinator.on_ws_reconnect
        return
    self._poll_bar()
```

**Почему inline:** S7 ws-private-consumer.md упоминает `check_alive` worker как S8 follow-up. Trader-expert выбрал inline — eliminates same-cadence race (две worker thread проверяют WS state одновременно). Total runtime threads = 2 (main + pybit). Меньше locks нужно.

### 5. KILL_SWITCH — sentinel-file CLI (Q4 REVISE; U2 user choice)

**Что:**
- `python -m src kill` (CLI subcommand) writes `.kill_switch` file в working directory.
- Main thread каждый tick (или каждый bar — TBD plan) checks `Path(".kill_switch").exists()`. Если да → set `halt_reason=KILL_SWITCH_REQUESTED`, drain in-flight order events, exit cleanly (не os._exit).

```python
# src/runtime/manager.py
def _maybe_kill_switch(self):
    if self._kill_switch_path.exists():
        self._coordinator.request_halt("KILL_SWITCH_REQUESTED")
        self._stopping = True
```

**Почему sentinel-file а не SIGUSR1:**
- **(a) SIGUSR1 — отвергнут:** возможен conflict с systemd/launchd supervisor semantics если bot wrapped. macOS launchd использует SIGUSR* для своих purposes.
- **(b) Sentinel-file — выбран:** cross-platform, no signal collision, deterministic поведение под supervisor. Trade-off: latency = 1 tick (5s) — приемлемо для manual operator action.

**Cleanup:** `python -m src run` на startup удаляет старый `.kill_switch` если существует (stale из прошлой сессии). Иначе процесс не сможет стартовать.

### 6. `HALT_RUNTIME_CRASH` mandatory (Q5 REVISE)

**Что:** RuntimeManager.run() обёрнут top-level `try/except`:

```python
def run(self):
    try:
        self._main_loop()
    except KeyboardInterrupt:
        self._shutdown(reason="KEYBOARD_INTERRUPT")
    except Exception as e:
        logger.exception("runtime crash")
        self._coordinator.request_halt("HALT_RUNTIME_CRASH")
        self._shutdown(reason="HALT_RUNTIME_CRASH", crash=e)
        raise
```

**Почему:** unhandled exception без halt persistence = next restart не знает о crash → может try `start_bracket` на corrupted state. `HALT_RUNTIME_CRASH` пишется в `halt_reason` (primary-wins по S7 γ rule) ДО re-raise → restart видит persisted halt → требует MANUAL_RESET → operator проверяет логи.

### 7. `RuntimeManager` class (Q3 CONFIRM, Q18 CONFIRM)

**Файл:** `src/runtime/manager.py` (NEW package `src/runtime/`).

**Public API:**
```python
class RuntimeManager:
    def __init__(
        self,
        *,
        coordinator: Coordinator,
        reconciler: Reconciler,
        ws_consumer: BybitPrivateWSConsumer,
        bar_source: BarSource,           # REST kline poller
        strategy: Strategy,
        settings: Settings,
    ) -> None: ...
    
    def run(self) -> None: ...              # blocking; main entry
    def shutdown(self, *, reason: str) -> None: ...  # graceful drain
```

**Owns all loops (Q18):** bar poll, check_alive inline, sentinel-file poll. NOT delegated to sub-objects. Single shutdown coordination point.

**Sequencing invariant (закрепляется S7 sub-decision 1):** `coordinator.bootstrap()` вызывается **first** в `run()`, до `ws_consumer.start()`, до bar polling. Assert `_bootstrap_done` уже existed в Coordinator (S7).

### 8. Sequential bar → signal → bracket (Q14 CONFIRM)

**Что:** в одном tick:
1. `bar = bar_source.poll()` (если new bar)
2. `signal = strategy.on_bar(bar)` (compute on close(T))
3. Если `signal.action == LONG`: `coordinator.start_bracket(signal)` (will be filled at open(T+1) — Bybit Market order semantics)

Внутри tick — никакого concurrency. pybit thread может trigger `on_order_event` параллельно — защищено lock'ом из sub-decision 1.

**Look-ahead invariant:** `strategy.on_bar` получает только closed bars. Catch-up bars (sub-decision 2) проходят через `strategy.warmup(bar)` (no signal emit), не `on_bar`.

### 9. Entry-point `python -m src` (Q10 REVISE)

**Файл:** `src/__main__.py` + `argparse` с subcommands.

```bash
python -m src run                  # start RuntimeManager (blocking)
python -m src backfill --from DATE --to DATE  # OHLCV backfill (existing scripts)
python -m src reconcile-only       # bootstrap + reconcile, no trading loop
python -m src kill                 # write .kill_switch sentinel
```

**Почему `python -m src` а не `bot`:** package называется `src` (см. `pyproject.toml`). Нет console_script entry в setup. Не создаём — adds packaging complexity без выигрыша в v0.1.

### 10. Удалить `src/controller.py` + `main.py` (Q17 REVISE)

**Что:** обa файла — orphan, broken since S2 venue migration:
- `src/controller.py` — imports gone modules (`src.data.consumer`, `src.strategy.strategy`, `src.risk.risk_manager`, `src.execution.executor`).
- `main.py` (repo root) — `from src.controller import Controller` → ImportError.

Заменяются на `src/runtime/manager.py` + `src/__main__.py`. Никаких `git mv` — clean delete + new files.

**TDD coverage:** удалить тесты которые ссылаются на controller (если есть). `tests/` audit перед deletion.

### 11. Settings additions (Q16 REVISE)

```python
# src/platform/config.py
class Settings:
    # NEW
    runtime_bar_poll_cadence_seconds: float = 5.0
    runtime_bar_poll_stall_threshold: int = 24       # validator: 6 ≤ N ≤ 720
    runtime_kill_switch_path: str = ".kill_switch"
    runtime_ws_check_alive_max_silence: float = 30.0
    runtime_warmup_bars: int = 50                    # для EMA(26)+ADX(14) seed
    # NOT added (Q8 REVISE — defer to S8b)
    # wallet_disagreement_epsilon: removed
    # check_alive_interval: removed (inline-call eliminates schedule)
```

**Naming:** underscore convention (pydantic-settings env var auto-mapping `RUNTIME_BAR_POLL_STALL_THRESHOLD`). Никаких dot-paths.

### 12. Reason codes (Q13 REVISE) — 42 → 45

| Code | Name | Class | Trigger |
|---|---|---|---|
| 43 | `HALT_RUNTIME_CRASH` | halt | unhandled exception в RuntimeManager.run() |
| 44 | `HALT_BAR_POLL_STALL` | halt (signal-pipeline) | N consecutive REST kline failures (default N=24) |
| 45 | `KILL_SWITCH_REQUESTED` | halt (operator) | sentinel-file `.kill_switch` detected |

Все три — halts, требуют MANUAL_RESET (operator-acknowledged). Primary-wins persistence по S7 γ rule.

### 13. Structlog KV events (Q11 CONFIRM)

Минимальный event vocabulary v0.1:

```
runtime.start                {symbol, settings_hash}
runtime.bootstrap_complete   {fsm_state, halt_reason}
runtime.ws_disconnect        {silence_seconds, action}
runtime.bar_tick             {bar_close_ts, last_seen_ts}
runtime.bar_poll_stall       {consecutive_failures, threshold}
runtime.kill_switch_detected {sentinel_path}
runtime.crash                {exc_type, exc_msg}
runtime.shutdown             {reason, in_flight_orders}
```

Все events — `logger.info`/`logger.error` с structured fields. Никаких free-form messages для machine-parseable post-mortem.

### 14. Tests (Q12 CONFIRM)

**Unit (mandatory):**
- `tests/unit/test_runtime_manager.py` — bootstrap → tick → shutdown invariants, kill-switch detection, crash → halt persistence.
- `tests/unit/test_bar_poller.py` — dedup, stall counter, recovery from transient failure.
- `tests/unit/test_coordinator_threading.py` — concurrent `on_order_event` + `start_bracket` (threading.Thread fixtures), assert FSM consistent.
- `tests/unit/test_reconciler_threading.py` — concurrent `on_wallet_event` + `reconcile`.
- `tests/unit/test_strategy_warmup_no_signal.py` — catch-up bars → 0 signals emitted.
- `tests/unit/test_kill_switch_cli.py` — `python -m src kill` writes file; `run` cleans stale file.
- `tests/unit/test_main_module.py` — argparse subcommand routing.

**Integration (opt-in `RUN_DEMO=1`):**
- `tests/integration/test_runtime_demo_smoke.py` — full bring-up на Demo Mainnet, 1 bar tick (или 0 trades если no signal), graceful shutdown.

**Property tests:** none new в S8a (S7 reconnect-idempotency покрывает FSM).

## Consequences

**Положительные:**
- Bot стартует end-to-end. `python -m src run` = working trading process.
- Closes ADR 0021 line 364 deferral (KILL_SWITCH wired).
- Убраны legacy orphans → меньше confusion для следующего contributor'а.
- Threading lock policy — основа для S9+ multi-bracket (RLock уже на месте).

**Negative / cost:**
- 2 thread workload (main + pybit) — небольшой operational footprint, нo нужен operator awareness.
- Sentinel-file KILL_SWITCH добавляет 1-tick latency vs signal (5s). Acceptable for manual operator action.
- Lock contention минимальный (10s tick + occasional WS event), но при S9+ multi-bracket надо будет re-evaluate.

**Затронутые файлы (новые / изменённые):**

**Source:**
- `src/runtime/__init__.py` — NEW package.
- `src/runtime/manager.py` — NEW `RuntimeManager`.
- `src/runtime/bar_source.py` — NEW REST kline poller.
- `src/__main__.py` — NEW argparse entry.
- `src/execution/coordinator.py` — Task 0: add `_lock = RLock()`, wrap 6 methods.
- `src/execution/reconciler.py` — Task 0: add `_lock = Lock()`, wrap 2 methods.
- `src/execution/state_machine.py` — add `KILL_SWITCH_REQUESTED` event handling (если ещё не существует — verify в S7 graph).
- `src/execution/reason_codes.py` (или enum-host file) — добавить codes 43, 44, 45.
- `src/platform/config.py` — 5 new settings + validator.
- **DELETE:** `src/controller.py`, `main.py` (root).

**Tests:** см. sub-decision 14.

**Migrations:** none. Reason codes — Python enum, не SQL.

**Wiki updates (Stage E):**
- NEW `wiki/project/components/runtime-manager.md` (entry-point, lifecycle, lock policy).
- NEW `wiki/project/components/bar-poller.md` (REST kline polling, stall semantics).
- UPDATE `wiki/project/components/ws-private-consumer.md` — driver loop now exists (cross-link к runtime-manager); `check_alive` callsite documented.
- UPDATE `wiki/project/components/execution-state-machine.md` — `KILL_SWITCH_REQUESTED` reason; lock policy link.
- UPDATE `wiki/project/components/reconciler.md` — lock policy.
- UPDATE `wiki/trading/concepts/reason-codes.md` — 42 → 45.
- UPDATE `wiki/project/architecture/risk-register.md` — add `POLL_STALL_MID_BAR_FILL` degradation scenario.
- UPDATE `wiki/project/runbooks/halt-recovery.md` — sections для `HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED`; SQL templates.

**Breaking changes:** none external. Internal: Coordinator/Reconciler methods теперь acquire lock — performance overhead negligible.

## Alternatives considered

**Alt-1: asyncio event loop** (single-thread async). Reject: full rewrite Coordinator/Reconciler from sync to async + pybit integration awkward (pybit threading internal). Defer S9+ если throughput требует.

**Alt-2: SIGUSR1 signal для KILL_SWITCH** (Q4 alternative). Reject: supervisor (systemd/launchd) collision risk. User explicitly chose sentinel-file (U2).

**Alt-3: WS+REST wallet epsilon-halt** в S8a (Q8 alternative). Reject: trader-expert verdict — REST canonical per ADR 0020 sub-decision 4. Halting on REST≠WS inverts hierarchy. Defer S8b.

**Alt-4: Separate check_alive worker thread** (Q6 alternative). Reject: same-cadence race с bar poller, лишний lock. Inline simpler.

**Alt-5: `runtime_bar_poll_stall_threshold = 12`** (U1 first-pass, ~60s halt). Reject: trader-expert round 2 — false-halt cost dominates given OCO bracket exchange-side preserves position safety; 24 (~120s) better balance.

**Alt-6: Keep src/controller.py + main.py** "for backwards compat". Reject: nothing depends on them; they're broken; YAGNI.

**Alt-7: S8 как один спринт (runtime + Analytics).** Reject: B1 principle — одна подсистема per спринт. Analytics требует execution topic + per-fill schema migration — отдельный scope. S8a→S8b sequencing.

## Open questions → deferred to S8b+

- WS+REST wallet consistency check (epsilon-halt) — S8b если operational evidence показывает frequent divergence.
- `execution` topic subscription + per-fill Analytics table — S8b.
- WS consumer dedicated health check threshold (separate from bar poller) — S8b/S9. Tighter cadence (~3 ticks @ 15s) because WS failure = position-safety event (per trader-expert annotation).
- Risk-dashboard external override REST endpoint — v0.2.
- Multi-symbol / multi-bracket concurrency — S9+ (lock granularity re-evaluation needed).
- Async/await migration — S9+ если throughput требует.
- systemd/launchd service unit — ops artifact, post-tag.

## Verification checklist (pre-merge)

- [ ] Task 0 lock wrappers acquired в Coordinator (6 methods) + Reconciler (2 methods) — verified by `grep "with self._lock"`.
- [ ] Threading test (2-thread fixture) — `on_order_event` × `start_bracket` parallel → FSM consistent; ditto `on_wallet_event` × `reconcile`.
- [ ] Bar poller dedup test: same `bar_close_ts` polled twice → emit once.
- [ ] Bar poller stall test: 24 consecutive failures → `HALT_BAR_POLL_STALL` set; 23 failures → recovery без halt.
- [ ] Strategy warmup test: 50 catch-up bars → 0 `on_signal` calls; first new bar after startup → 1 signal.
- [ ] KILL_SWITCH test: `python -m src kill` writes file; `RuntimeManager._tick` detects → graceful shutdown; stale file removed на startup.
- [ ] HALT_RUNTIME_CRASH test: forced exception в `_main_loop` → `halt_reason` persisted ДО re-raise.
- [ ] Settings validator: `runtime_bar_poll_stall_threshold` rejects N<6 и N>720.
- [ ] `src/controller.py` + `main.py` deleted; `pytest --collect-only` passes (no broken imports).
- [ ] `python -m src run --help` shows argparse subcommands (run/backfill/reconcile-only/kill).
- [ ] Integration test (Demo Mainnet, `RUN_DEMO=1`): full bring-up completes; graceful shutdown via kill switch.
- [ ] Wiki Stage E: 2 new component pages + 5 updated + runbook update + risk-register update.
- [ ] `~/.claude/agents/trading-logic-reviewer.md` synced if new invariants added (lock policy, stall halt class).

---

**Approved:** 2026-04-24 by maintainer (user) after trader-expert verdict (rounds 1+2).
