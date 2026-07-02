# PINNED_VERSIONS — реестр явных пинов моделей (ADR 0075)

Источник истины «почему этот агент на этой версии». kit-auditor diff'ает против этого файла; пин без строки здесь = cargo-cult (findable-stale). Обновлять при смене пина + `last-reviewed` при ревью-триггере (новый платформенный дефолт).

| Agent | Model pin | Reason | Last-reviewed |
|---|---|---|---|
| architecture-reviewer | claude-fable-5 | judgment-heavy, high-blast (кросс-модульные решения кита); Matrix §4.1 | 2026-07-02 |
| trader-expert | claude-fable-5 | judgment-heavy (PHASE 2 доменные вердикты); Matrix §4.1 | 2026-07-02 |
| security-auditor | claude-fable-5 | judgment-heavy, high-blast (money/secret/bypass — S61 нашёл BLOCKER) | 2026-07-02 |
| doc-linker | claude-fable-5 | семантические связи (opus-класс для качества графа) | 2026-07-02 |
| doc-reviewer-depth | claude-fable-5 | построчная сверка docs против кода (точность) | 2026-07-02 |
| doc-writer | claude-sonnet-5 | draft-качество, не judgment-heavy — тир дешевле. **OQ-6: подтвердить намеренность** | 2026-07-02 |
| trading-logic-reviewer | claude-sonnet-5 | standard-тир money-код ревью, воспроизводимость вердиктов | 2026-07-02 |
| quant-stats-reviewer | claude-sonnet-5 | standard-тир math/stat ревью, воспроизводимость | 2026-07-02 |
| data-integrity-reviewer | claude-sonnet-5 | standard-тир storage/schema ревью | 2026-07-02 |
| dashboard-reviewer | claude-sonnet-5 | standard-тир UI ревью | 2026-07-02 |
| bybit-api-reviewer | claude-sonnet-5 | standard-тир API-protocol ревью | 2026-07-02 |
| test-engineer | claude-sonnet-5 | standard-тир test-strategy | 2026-07-02 |
| kit-auditor | claude-fable-5 | judgment-heavy kit-integrity (S63) | 2026-07-02 |
| merge-analyst | claude-fable-5 | judgment-heavy pre-merge риск (S63) | 2026-07-02 |
| release-manager | claude-fable-5 | judgment-heavy ship-оркестрация (S63) | 2026-07-02 |

**ВАЖНО (arch HIGH #2 fix):** `claude-sonnet-5` — это ЯВНЫЙ версионный пин, НЕ алиас `sonnet`. Все явные пины `claude-*-N` перечислены в таблице выше (иначе pin-аудит kit-auditor пометит их UNREGISTERED). Строки ниже — ТОЛЬКО настоящие алиасы (без версии).

## Настоящие алиасы (авто-трек дефолта, без версии — не пинятся)
- `frontend-developer` → `opus` (было `claude-opus-4-7` stale — S63 fix; не kit-work, low-maintenance).
- `python-reviewer`, `doc-reviewer` → `haiku` (механический lint-style / consistency).

## Правило (ADR 0075)
PIN версию → judgment-heavy + причина записана. Алиас → механическое/low-risk. Пин без причины здесь = stale по умолчанию.
