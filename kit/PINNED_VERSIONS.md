# PINNED_VERSIONS — реестр пинов моделей + effort (ADR 0077 tiered v3, суперседит 0076 uniform)

**Директива оператора 2026-07-02:** минимум токенов при максимуме результата. За потолок платим МОДЕЛЬЮ на дефолтном effort, не раздутым effort'ом на дешёвой (Opus-high > Sonnet-max: потолок надёжнее, overthinking-риск ниже). Tiered заменяет uniform-fable5 ADR 0076.

Источник истины «какая модель+глубина у агента». kit-auditor diff'ает против этого файла; пин без строки здесь = findable-stale. Все 18 агентов ниже. **effort — baseline в frontmatter; Workflow-dispatch переопределяет для эскалаций** (см. ADR 0077 «Dispatch-override»).

| Agent | Model pin | effort | Роль / почему этот тир | Last-reviewed |
|---|---|---|---|---|
| security-auditor | claude-opus-4-8 | high | деньги/секреты/обход авторизации — самый дорогой провал; new-surface→xhigh dispatch | 2026-07-02 |
| trading-logic-reviewer | claude-opus-4-8 | high | движок денежных решений, частый + высокая цена ошибки; потолок берём моделью | 2026-07-02 |
| quant-stats-reviewer | claude-opus-4-8 | high | S27-класс тонких мат-багов ловится потолком модели | 2026-07-02 |
| architecture-reviewer | claude-opus-4-8 | high | judgment-heavy кросс-модульные + pre-plan gate миграций | 2026-07-02 |
| trader-expert | claude-opus-4-8 | high | PHASE 2 доменные вердикты (bounded); ROUND 2→xhigh dispatch | 2026-07-02 |
| data-integrity-reviewer | claude-sonnet-5 | high | инварианты перечислимы → глубина effort'ом; defense-in-depth от Opus-тройки | 2026-07-02 |
| bybit-api-reviewer | claude-sonnet-5 | high | протокол Bybit V5 — перечислимые правила, не открытое суждение | 2026-07-02 |
| test-engineer | claude-sonnet-5 | high | coverage-анализ — тщательность, не IQ-потолок | 2026-07-02 |
| doc-writer | claude-sonnet-5 | high | генерация RU-текста — объём+стиль для оператора | 2026-07-02 |
| frontend-developer | claude-sonnet-5 | high | UI-execute (FastAPI+vanilla); миграции стека закрыты architecture-reviewer gate | 2026-07-02 |
| kit-auditor | claude-sonnet-5 | medium | 7 измерений механики — ширина контекста, не глубина | 2026-07-02 |
| dashboard-reviewer | claude-sonnet-5 | medium | UI/XSS/TIER-метрики чеклист, не денежное ядро | 2026-07-02 |
| doc-reviewer-depth | claude-sonnet-5 | medium | сверка доков против src (bounded); money-страницы→high dispatch | 2026-07-02 |
| doc-linker | claude-sonnet-5 | medium | граф ссылок + семантика — средняя глубина | 2026-07-02 |
| merge-analyst | claude-sonnet-5 | medium | предсказание гейтов по regex/паттернам | 2026-07-02 |
| release-manager | claude-sonnet-5 | medium | ship-чеклист перечислим; необратимость держат механические гейты | 2026-07-02 |
| python-reviewer | claude-haiku-4-5 | — | PEP8/идиомы — линт-класс, потолок модели не участвует (effort не поддержан) | 2026-07-02 |
| doc-reviewer | claude-haiku-4-5 | — | wiki consistency — lightweight sync-чеклист (effort не поддержан) | 2026-07-02 |

**Тиры:** 5 opus-4.8 + 11 sonnet-5 + 2 haiku-4.5 = 18. Fable-5 нигде как пин (остаётся ad-hoc инструментом для ручного deep-research/adversarial-hunt через Workflow).

## Правило (ADR 0077 — tiered, суперседит 0076 uniform)
Модель = frontmatter-пин по фазе×роли (потолок). effort = frontmatter-baseline (детерминизм) + Workflow-dispatch-override для 4 эскалаций (trader-expert R2 xhigh / security-auditor new-money-surface xhigh / doc-reviewer-depth money-страницы high / execute длинная-TDD xhigh + blocked-2× opus-xhigh). `max` — только ручная эскалация когда xhigh упёрся, НЕ пин/триггер. Haiku — без effort-поля (400-ошибка). Новый агент → sonnet-5 high по умолчанию; opus только judgment/money-critical, haiku только lint-класс. Ревью-триггер: смена платформенного дефолта ИЛИ директива оператора.
