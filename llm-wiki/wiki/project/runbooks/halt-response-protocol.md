---
title: Halt response protocol — P0 wake + alpha.11 rollback + RC iteration
type: runbook
tags: [operator, halt-response, rollback, sprint-12, p0-critical]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/runbooks/halt-recovery.md
---

# Halt response protocol — P0 wake + rollback

**TL;DR:** When P0 halt fires (CRITICAL severity per [[halt-recovery]] priority matrix), operator wake immediately, diagnose, decide rollback OR forward-fix. RC tag iteration enables iterative S12 fix attempts WITHOUT contaminating final v0.1.0-alpha.12 release.

## Decision tree

```
P0 halt fires
   │
   ├── Bot still running? → Kill via `python -m src kill --reason P0_RESPONSE`
   │
   ├── Diagnose halt code (см. halt-recovery.md priority matrix entry)
   │
   ├── Recoverable WITH operator action в-place?
   │  ├── YES → Apply recovery procedure от halt-recovery.md
   │  │      → Re-run pre-flight gates → restart bot → continue 48h validation
   │  │
   │  └── NO → Halt is showstopper. Decide rollback OR forward-fix:
   │
   │      ├── Forward-fix viable (< 4h to ship)? → Implement fix, RC tag iteration:
   │      │   git checkout -b fix/s12-rc.N feature/sprint-12-...
   │      │   <implement fix> + commit + test
   │      │   git tag -a v0.1.0-alpha.12-rc.N -m "S12 RC.N: <fix description>"
   │      │   <restart 48h validation от scratch>
   │      │
   │      └── Rollback к alpha.11 (preserve operator infra):
   │          git checkout main
   │          git revert <S12_merge_sha> -m 1  # revert merge commit
   │          git push origin main
   │          # Database safe: Q7 zero-migration constraint preserved binary compat
   │          # Re-tag NOT needed (alpha.11 still ships latest stable)
   │          # File S13 reopen ticket для S12 root cause investigation
```

## P0 halt response checklist (do in order)

1. **Stop the bot** (если still running):
   ```bash
   python -m src kill --reason P0_RESPONSE_<halt_code>
   sleep 5
   ps -p $(cat /tmp/bot_pid.txt) > /dev/null && echo "STILL RUNNING" || echo "stopped"
   ```

2. **Capture state snapshot** (do BEFORE any further actions):
   ```bash
   python -m src monitor --symbol BTCUSDT > halt_snapshot_$(date +%Y%m%d_%H%M%S).txt
   sqlite3 ~/.ai_trading_bot/bot.db "SELECT * FROM halt_log ORDER BY halted_at DESC LIMIT 5" >> halt_snapshot_*.txt
   sqlite3 ~/.ai_trading_bot/bot.db "SELECT * FROM execution_state" >> halt_snapshot_*.txt
   ```

3. **Cross-check exchange-side state** (Bybit demo console):
   - Open positions: 0 expected (or matches `execution_state.bracket_id` если OCO_ARMED)
   - Open orders: 0 expected (or matches OCO bracket: 1 entry или 2 TP/SL)
   - Account balance: matches `execution_state.equity`?

4. **Diagnose** per [[halt-recovery]] priority matrix entry для specific halt_code.

5. **Decide rollback OR forward-fix:**

   **Forward-fix criteria (RC tag iteration):**
   - Root cause identified within 1h
   - Fix implementable + testable within 4h
   - Test coverage exists OR can be added в same sprint
   - Schema unchanged (Q7 constraint)

   **Rollback criteria (alpha.11):**
   - Root cause unclear after 1h investigation
   - Fix requires schema change (violates Q7)
   - Fix touches > 3 components (architectural concern)
   - 2nd P0 halt within 12h (validation environment unstable)

## Rollback procedure (alpha.11)

Q7 zero-migration constraint enables clean binary rollback:

```bash
# 1. Verify alpha.11 binary compatibility
git log --oneline v0.1.0-alpha.11..HEAD -- migrations/ src/
# Expected: src/ changes ОК (compatible code), migrations/ EMPTY (Q7 constraint)

# 2. Revert merge commit
git checkout main
git pull
git revert <S12_squash_merge_sha> -m 1
git push origin main

# 3. Verify tags unchanged (alpha.11 still latest stable)
git tag --sort=-v:refname | head -3

# 4. Restart pre-flight + validation от scratch на alpha.11
git checkout v0.1.0-alpha.11
source .venv/bin/activate
python -m src reconcile-only --symbol BTCUSDT
# Expected: bootstrap clean

# 5. File S13 reopen ticket
echo "## S13 carry-over: S12 P0 rollback root cause" >> wiki/project/SPRINT_STATE.md
echo "halt_code: <code>, snapshot: halt_snapshot_*.txt" >> wiki/project/SPRINT_STATE.md
```

## RC tag iteration procedure

```bash
# After forward-fix implemented + tested
git add <fixed files>
git commit -m "fix(s12): rc.N — <root cause + fix description>"
git tag -a v0.1.0-alpha.12-rc.N -m "S12 RC.N: <one-line summary>"
git push origin v0.1.0-alpha.12-rc.N

# Restart 48h validation (start counter от 0)
# Document в sprint-12 page: "RC.N attempted, root cause: <X>, fix: <Y>"
```

Iterate RC.1, RC.2, ... до final clean 48h run. Then ship final `v0.1.0-alpha.12` (drop -rc suffix).

## Conditional escalation (P1 → P0)

Per Q7 trader concern: `HALT_EXCHANGE_OUTAGE` (P1 RECOVERABLE) → escalate к **P0 if state == OCO_ARMED + outage > 1h**:
- Bot might have open OCO bracket whose TP/SL не armed before outage
- Position exposed without protection
- Operator MUST verify exchange-side state (positions + open orders) BEFORE restart
- Treat as P0 wake; do not auto-resume

См. полный escalation rule в [[halt-recovery]] "Conditional P1→P0 escalation" section (added в S12 T3).

## Related

- [[halt-recovery]] — halt code reference + priority matrix
- [[live-demo-validation]] — entry context для when this runbook fires
- [[pre-flight]] — pre-restart entry gates after rollback
- [[../decisions/0027-sprint-12-live-demo-validation]] — Q7 verdict trail
