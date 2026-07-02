---
title: "0077. Model pin — tiered v3 (opus/sonnet/haiku по фазе×роли + effort в frontmatter, суперседит 0076 uniform)"
type: decision
status: accepted
created: 2026-07-02
updated: 2026-07-02
---

# 0077. Tiered pin-policy v3 (opus-4.8 / sonnet-5 / haiku-4.5 + effort)

**Status:** accepted (директива оператора 2026-07-02)
**Supersedes:** [[0076-model-pin-uniform-fable5]]

## Контекст

ADR 0076 (uniform `claude-fable-5` ×18) исходил из «токен-бюджет не ограничен, качество > дешевизна». Оператор пересмотрел цель: **минимум токенов при максимуме результата** — fable-5+max на КАЖДОМ агенте (в т.ч. lint/consistency/draft) = переплата без выигрыша. Свежие официальные доки (platform.claude.com/effort + models overview, прочитаны 2026-07-02) дали факты, отсутствовавшие при 0076:

- **`high` = дефолт Anthropic**, «exactly the same behavior as omitting the parameter», «often the sweet spot balancing quality and token efficiency».
- **`xhigh`** = «long-running agentic tasks (over 30 minutes) with token budgets in the millions» + «meaningfully higher token usage than high». Наши ревьюеры делают ОДИН проход по диффу (минуты) — xhigh не окупается.
- **`max`** = «reserve for genuinely frontier problems… significant cost for relatively small quality gains… can lead to overthinking», прямо про structured-output (вердикты ревьюеров структурированы).
- **Haiku effort не поддержан** («will error on Sonnet 4.5 / Haiku 4.5»).
- Позиционирование: Opus 4.8 = «complex agentic coding and enterprise work»; Sonnet 5 = «best combination of speed and intelligence», «close to Opus 4.8 at lower prices»; Haiku = «fastest with near-frontier intelligence».

## Решение

**Принцип: за потолок платим МОДЕЛЬЮ на дефолтном effort, а не раздутым effort'ом на дешёвой модели.** Opus-high надёжнее Sonnet-max (потолок Sonnet ≈ 4.5/4.6-уровень; S27-класс тонких мат-багов ловится потолком модели, не глубиной effort). Effort управляет ТЩАТЕЛЬНОСТЬЮ (сколько tool-calls / как глубоко), модель — ПОТОЛКОМ интеллекта.

**Пины (frontmatter `model:` + `effort:` — baseline; Workflow-dispatch переопределяет effort для эскалаций):**

| Модель | effort | Агенты |
|---|---|---|
| `claude-opus-4-8` | high | trader-expert, architecture-reviewer, trading-logic-reviewer, quant-stats-reviewer, security-auditor |
| `claude-sonnet-5` | high | data-integrity-reviewer, bybit-api-reviewer, test-engineer, doc-writer, frontend-developer |
| `claude-sonnet-5` | medium | kit-auditor, dashboard-reviewer, doc-reviewer-depth, doc-linker, merge-analyst, release-manager |
| `claude-haiku-4-5` | — (нет поля) | python-reviewer, doc-reviewer |

Итого: 5 opus + 11 sonnet + 2 haiku = 18.

**Effort в frontmatter = baseline** (детерминированная глубина даже при dispatch через Agent tool, который effort не принимает). **Dispatch-override (Workflow `agent(…,{effort})`) для 4 эскалаций:**
- trader-expert ROUND 2 (adversarial re-research = exploratory) → `xhigh`.
- security-auditor ПЕРВЫЙ проход новой money-поверхности (override/HMAC/withdrawal/Mainnet — охота на неизвестные векторы) → `xhigh`.
- doc-reviewer-depth страницы денежного ядра (risk/kelly/DSR) → `high`.
- Execute-фаза: длинная multi-file TDD-задача → executor `xhigh`; blocked-2× / security-critical код → эскалация модели на `claude-opus-4-8` xhigh.

**`max` — нигде как постоянка/триггер-правило.** Единственный легальный кейс: ручная эскалация, когда `xhigh` уже упёрся на конкретной задаче (доки: max = diminishing returns / overthinking-риск).

## Экономика (блендед $/MTok × effort-множитель; интро-цена Sonnet до 2026-08-31)

| Вариант | усл. ед. | vs прод |
|---|---|---|
| Прод 0076 (fable5+max ×18) | 792 | — |
| v3 (этот ADR) | ~99 | **8× дешевле, −87%** |

Якорь из сессии: Verify-фаза одного deep-research = 3.8M токенов / 63 fable5-агента ≈ $84 за ОДНУ фазу; рутинное ревью повторяется каждый спринт — множитель копится постоянно.

## Что НЕ теряем (обоснование «дешевле ≠ хуже»)

- Топ-5 (security/trading-logic/quant-stats/architecture/trader-expert) на Opus-high — уровень, который доки называют «excellent results»; Fable5-преимущество (multi-hour автономность, enterprise-с-нуля) рутинному «проверь диф» не нужно.
- Чеклист-ревьюеры (bybit-api/data-integrity/test-engineer/…) — тщательность куплена effort'ом на Sonnet, не переплатой за потолок; defense-in-depth: Opus-тройка сидит на тех же money-путях.
- python-reviewer/doc-reviewer — линт-класс, потолок модели в результате не участвует.

## Последствия

- `kit/PINNED_VERSIONS.md` переписан: 18 строк, 3 тира + effort + причина.
- Оба дерева агентов (`kit/agents/` + `~/.claude/agents/`) — `model:` + `effort:` per таблица; `diff -rq` clean.
- kit-auditor (dim-8 pin-registry): ожидание = tiered (5 opus / 11 sonnet / 2 haiku); любой fable-5 пин = drift.
- **Триггер ревью (сохранён):** смена платформенного дефолта модели ИЛИ явная директива оператора. Пин ≥2 релиза позади = HARD-STALE. `last-reviewed` в реестре.
- **`max`-политика применения:** effort-эскалации живут в диспетч-правилах контроллера (этот ADR + kit-conventions), НЕ в frontmatter.

## Связано
[[0076-model-pin-uniform-fable5]] (superseded) · [[0075-model-pin-policy-v2]] · [[0074-runtime-tuning]] · `kit/PINNED_VERSIONS.md` · kit-auditor агент · память `agent-body-hygiene`
