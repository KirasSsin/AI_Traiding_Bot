---
title: bybit-api-reviewer (L5 reviewer agent — Bybit V5 API protocol correctness)
type: component
tags: [agent, l5-reviewer, bybit, v5-api, sonnet, sprint-32d, kit-phase-3]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - ~/.claude/agents/bybit-api-reviewer.md
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/decisions/0016-bybit-venue-migration.md
  - project/decisions/0020-spot-oco-emulation.md
  - project/sprints/sprint-02-bybit-venue-migration.md
---

# bybit-api-reviewer (L5 reviewer agent)

**TL;DR:** L5 reviewer agent specialized для Bybit V5 Spot API protocol correctness. Sonnet model. 6-axis review: rate limits / order param validation / WebSocket schema / error code handling / pagination / HMAC SHA256 signing.

## Block 1 — Code refs

| Element | Anchor |
|---------|--------|
| Agent prompt | `~/.claude/agents/bybit-api-reviewer.md` (out-of-repo) |
| Scope target | `src/execution/bybit/{adapter,ws_private,rest,errors}.py` + `src/marketdata/` Bybit code paths |
| Created in | ADR 0048 (Sprint 32d Kit Phase 3) |
| Trigger pattern | After Bybit API code change OR pre-merge для sprints touching Bybit surface |

## Block 2 — Description

### Назначение

L5 domain reviewer заполняет gap между:
- `trading-logic-reviewer` — business logic, FSM transitions, reason codes (does NOT check Bybit API protocol details)
- `data-integrity-reviewer` — storage, migrations, Parquet (does NOT check API client correctness)
- `architecture-reviewer` — cross-module, DI, API stability (does NOT check exchange-specific protocol)

bybit-api-reviewer = SPECIALIST для Bybit V5 protocol compliance. Knows Bybit-specific:
- Rate limits (600 req/min spot, 60 orders/sec)
- Param precision rules (`lotSizeFilter.qtyStep`, `priceFilter.tickSize`)
- retCode semantics (10001-10010 / 110001-170134 / 33004)
- WebSocket V5 message schema (data list vs V3 single dict)
- HMAC SHA256 sign format (REST + WS auth)

### Когда invoke

- ANY change в `src/execution/bybit/` module
- ANY new pybit V5 invocation в codebase
- Pre-merge для sprints touching Bybit API surface
- Post-implementation для Bybit feature additions

### Не scope

- Trading strategy logic → `trading-logic-reviewer`
- Math formulas → `quant-stats-reviewer`
- Storage / migrations → `data-integrity-reviewer`
- Generic Python → `python-reviewer` (after bybit-api-reviewer)
- Money/security trading state mutation → `security-auditor` (вместе с bybit-api-reviewer для money-touching Bybit code — например withdrawal endpoints if implemented)
- Dashboard FastAPI / vanilla JS → `dashboard-reviewer`

### Review checklist (6 axes)

1. **Rate limits** — Spot REST 600 req/min, order 60/sec, WebSocket 10 topics/connection, exponential backoff на 429/10006
2. **Order parameter validation** — qty precision (lotSizeFilter), price tick (priceFilter), min order qty/amt, TIF (GTC/IOC/FOK), side/orderType case-sensitive
3. **WebSocket message schema** — V5 data list, ms timestamps, execId/orderId/orderLinkId preservation, status enum exhaustive match, ping/pong heartbeat 30s, re-subscribe after reconnect, auth required для private
4. **Error code handling** — retCode != 0 handled, 10006 backoff retry, 110001 reconcile path, 110007/170131 halt, unknown retCode log + UNKNOWN reason
5. **Pagination** — cursor field, bound by since_ts < now(), limit ≤ 1000, time alignment к interval, no look-ahead, gap detection
6. **HMAC SHA256 signing** — exact V5 format, recv_window ≤ 5000ms, NTP sync, WS auth `expires + sign GET/realtime`, no api_secret в logs/exceptions

### Output format

Per `superpowers:requesting-code-review`: Blockers / Concerns / Verified / Follow-ups for wiki.

Severity: BLOCKER (production risk: rate limit overflow / wrong order / signature broken / secret leak) / HIGH (correctness gap) / MEDIUM (robustness) / LOW (style).

### Configuration

| Setting | Value |
|---------|-------|
| Model | claude-sonnet-4-5 |
| Memory | project (auto-creates `.claude/agent-memory/bybit-api-reviewer/MEMORY.md` on first WRITE) |
| Tools | Read, Grep, Glob, Bash, WebFetch (Bybit docs URL access) |

### Why specialized agent (vs trading-logic-reviewer extension)?

Trading-logic-reviewer focuses на business logic correctness (entry/exit conditions, risk sizing, halt thresholds). API protocol correctness = orthogonal concern, requires Bybit-specific knowledge (retCodes, schema versions, sign format) that pollutes trading-logic-reviewer prompt.

Splitting:
- trading-logic-reviewer = "is this business logic correct?"
- bybit-api-reviewer = "is this Bybit V5 protocol correctly used?"

Both can run parallel via `superpowers:dispatching-parallel-agents`.

## Related

- [[../decisions/0017-review-agent-harness]] — L5 agent matrix policy
- [[../decisions/0016-bybit-venue-migration]] — Bybit V5 chosen (S2)
- [[../decisions/0020-spot-oco-emulation]] — execution layer (S6)
- [[../decisions/0022-live-runtime-reconciler]] — WebSocket reconciler (S8a)
- [[../decisions/0048-sprint-32d-kit-phase-3-improvements]] — этот agent создан здесь
- [[../sprints/sprint-02-bybit-venue-migration]] — S2 (initial Bybit integration)
- [[../sprints/sprint-08a-live-runtime]] — S8a (WebSocket private stream)
- [[../sprints/sprint-32d-kit-phase-3-improvements]] — S32d (этот agent ship)
- [[bybit-adapter]] — adapter component
- [[bybit-rest]] — REST client component
- [[bybit-ws]] — WebSocket consumer component
