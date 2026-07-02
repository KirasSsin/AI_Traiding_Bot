---
title: review-gate — механический барьер Фазы 6 (ревью денежного ядра)
type: component
tags: [kit, hook, enforcement, review, money-core]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/hooks/review-gate.sh]
status: stable
---

# review-gate — деньги не мержатся без ревью

**TL;DR:** `gh pr merge` / `git merge feature/sprint-*` при диффе, трогающем денежные пути (`src/signalgen|execution|risk|backtest`, override) — блокируется, пока нет обоих артефактов Фазы 6: `| 6 Review | done |` в SPRINT_STATE **и** `reviews/review-sNN.md` со строкой `Blockers: 0`. S59, KIT-003.

## Зачем
S55: доменные ревьюеры поймали 2 BLOCKER (TL-01 unbounded-loss OCO; BYBIT-01 testnet/mainnet рассинхрон), прошедшие ручное ревью. До S59 самая дорогая фаза не имела механического гейта — мердж был возможен при Phase5=done и пропущенной Фазе 6.

## Механика
Дифф `main...<ref>` (ref: sprint-ветка из команды или текущая при `gh pr merge`); docs/kit-only диффы проходят свободно. Fail-OPEN на инфра-ошибках. Формат review-файла: список ревьюеров + вердикты + `Blockers: 0`.

## Проверено (S59 red/green)
money-diff без артефактов → exit 2; с артефактами → `✓ Review gate OK`; docs-only → пропуск.

## Related
- [[../architecture/sprint-flow-ru]] Фаза 6 · [[adr-agent-sync-hook]] · [[hooks-selfcheck-hook]]
