---
title: "0075. Model pin-policy v2 — когда пинить версию vs алиас"
type: decision
status: superseded
created: 2026-07-02
updated: 2026-07-02
---

# 0075. Model pin-policy v2 (S63)

**Status:** superseded by [[0076-model-pin-uniform-fable5]] (оператор 2026-07-02 — uniform fable-5, mixed-tier отменён)
**Date:** 2026-07-02

## Контекст (P2-PINPOLICY)

Пины моделей агентов — смесь версий (`claude-fable-5`, `claude-opus-4-7`) и алиасов (`sonnet`, `opus`) без записанной политики «когда что». Обнаружен stale-пин: `frontend-developer=claude-opus-4-7` (устарел, никакого ADR/комментария). Спроектировано через Workflow (architecture-reviewer, fable-5).

## Решение

**Правило пиннинга:**
- **PIN явной версии** (`claude-fable-5`, `claude-opus-4-8[1m]`), когда: (1) judgment-heavy / high-blast-radius работа, где кросс-сессионная воспроизводимость важнее авто-апгрейда; (2) промпт тюнен под квирки конкретного снапшота (reasoning-effort, tool-call стиль); (3) **текстовая причина ЭТОЙ версии записана**.
- **Алиас** (`opus`/`sonnet`/`haiku`, без версии), когда: механическая/low-risk работа (scaffolding, lint-style ревью, счётчики) — алиас авто-трекает платформенный дефолт и НЕ может протухнуть.
- **Пин без записанной причины = cargo-cult**, по умолчанию findable-stale на следующем аудите.

**Триггер ревью (BINDING):** при выходе нового платформенного дефолта за алиасом — ВСЕ агенты с явным пином проходят re-review в следующем kit-спринте: kit-auditor grep'ает `model: claude-<tier>-<version>`, для каждого проверяет валидность причины; пин ≥2 релиза позади → HARD-STALE. Требует реестра `kit/PINNED_VERSIONS.md` (agent→version→reason→last-reviewed) — единственный практичный источник «что актуально сейчас» (агенты не видят release notes).

## Последствия

- Создан `kit/PINNED_VERSIONS.md` — реестр 6 fable-5 пинов + причины + дата.
- `frontend-developer`: `claude-opus-4-7` (stale) → алиас `opus` (не kit-work, low-maintenance → авто-трек).
- kit-auditor (S63) при аудите пинов diff'ает против реестра.
- Открытый вопрос → OPERATOR-QUEUE: `doc-writer=sonnet-5` — намеренный дешёвый тир или gap миграции? (не блок).

## Связано
[[0074-runtime-tuning]] · [[../architecture/kit-overview-ru]] · kit-auditor агент (S63)
