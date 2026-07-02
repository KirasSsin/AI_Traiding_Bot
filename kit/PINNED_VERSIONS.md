# PINNED_VERSIONS — реестр явных пинов моделей (ADR 0076 uniform, суперседит ADR 0075)

**Директива оператора 2026-07-02:** ВСЕ агенты на `claude-fable-5` (max-качество, токен-бюджет не ограничен, нужна глубокая проработка). При срабатывании safety-правила fable-5 → авто-переключение на `claude-opus-4-8` max — **приемлемо** (оператор). Uniform-политика заменяет смешанные тиры ADR 0075.

Источник истины «какая версия у агента». kit-auditor diff'ает против этого файла; пин без строки здесь = findable-stale. Все 18 агентов = `claude-fable-5`.

| Agent | Model pin | Роль (контекст) | Last-reviewed |
|---|---|---|---|
| architecture-reviewer | claude-fable-5 | judgment-heavy кросс-модульные решения кита | 2026-07-02 |
| trader-expert | claude-fable-5 | PHASE 2 доменные вердикты | 2026-07-02 |
| security-auditor | claude-fable-5 | money/secret/bypass (S61 нашёл BLOCKER) | 2026-07-02 |
| doc-linker | claude-fable-5 | семантические связи графа docs | 2026-07-02 |
| doc-reviewer-depth | claude-fable-5 | построчная сверка docs против кода | 2026-07-02 |
| doc-writer | claude-fable-5 | генерация доков (OQ-6: поднят с sonnet) | 2026-07-02 |
| trading-logic-reviewer | claude-fable-5 | money-код ревью (uniform: поднят с sonnet) | 2026-07-02 |
| quant-stats-reviewer | claude-fable-5 | math/stat ревью (uniform: поднят с sonnet) | 2026-07-02 |
| data-integrity-reviewer | claude-fable-5 | storage/schema ревью (uniform: поднят с sonnet) | 2026-07-02 |
| dashboard-reviewer | claude-fable-5 | UI ревью (uniform: поднят с sonnet) | 2026-07-02 |
| bybit-api-reviewer | claude-fable-5 | API-protocol ревью (uniform: поднят с sonnet) | 2026-07-02 |
| test-engineer | claude-fable-5 | test-strategy (uniform: поднят с sonnet) | 2026-07-02 |
| kit-auditor | claude-fable-5 | kit-integrity аудит (S63) | 2026-07-02 |
| merge-analyst | claude-fable-5 | pre-merge риск-профиль (S63) | 2026-07-02 |
| release-manager | claude-fable-5 | ship-оркестрация (S63) | 2026-07-02 |
| frontend-developer | claude-fable-5 | UI-разработка (uniform: поднят с opus-алиаса) | 2026-07-02 |
| python-reviewer | claude-fable-5 | Python lint/idioms (uniform: поднят с haiku) | 2026-07-02 |
| doc-reviewer | claude-fable-5 | wiki consistency (uniform: поднят с haiku) | 2026-07-02 |

**Все пины = явный версионный пин `claude-fable-5`** (НЕ алиас). Алиасов больше нет — uniform-политика.

## Правило (ADR 0076 — uniform, суперседит ADR 0075 mixed-tier)
Все агенты = `claude-fable-5`. Нет дешёвых тиров/алиасов. Safety-fallback `claude-fable-5` → `claude-opus-4-8` max приемлем (оператор 2026-07-02). Новый агент → `claude-fable-5` по умолчанию. Ревью-триггер пина: смена платформенного дефолта fable-5 ИЛИ явная директива оператора о смене политики.
