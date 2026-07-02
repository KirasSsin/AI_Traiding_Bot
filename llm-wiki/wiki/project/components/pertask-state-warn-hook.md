---
title: pertask-state-warn — напоминание per-task протокола SPRINT_STATE
type: component
tags: [kit, hook, warn, sprint-state]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/hooks/pertask-state-warn.sh]
status: stable
---

# pertask-state-warn — WARN при коммите src/ без SPRINT_STATE

**TL;DR:** `git commit` со staged `src/**`, но без `SPRINT_STATE.md` → предупреждение в stderr (exit 0, НЕ блок). S59, KIT-013.

Правило Фазы 4: state обновляется после КАЖДОЙ задачи — иначе обрыв сессии теряет next_action (история S16–S27). WARN, а не блок — сознательно: не душим bugfix-флоу; эскалация до блока — по итогам наблюдений (телеметрия S62).

## Проверено (S59)
staged src/ без state → WARN, exit 0; со staged state → тишина.

## Related
- [[../architecture/sprint-flow-ru]] Фаза 4 per-task протокол · [[auto-resume]] (опирается на актуальный next_action)
