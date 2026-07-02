---
title: Backlog — kit op-detect hardening (dedicated security sprint)
type: backlog
created: 2026-07-02
status: open
source: S61 adversarial bypass-hunt rounds 4-6
---

# Backlog: op-detect устойчивость гейтов (выделенный security-спринт)

Открыто из 6-раундового adversarial bypass-hunt в S61 (обзор: [[reviews/review-s61]]). Все ПОДТВЕРЖДЁННЫЕ находки закрыты в S61; ниже — ОСТАТОК, требующий архитектурного, не патч-уровня, решения. Money-контур при этом защищён diff-детектом (review-gate primary money-path check по `main...ref` fires независимо от phase/строки команды).

## Что уже закрыто в S61 (не переделывать)
- phase-гейты fail-CLOSED на неканоничной phase (unicode/zero-width/мусор) — оба слоя (validator reject + gate arms).
- self-skip по подстроке имени скрипта УДАЛЁН (декой `# bash review-gate.sh` / `&& bash hook.sh` больше не обходит).
- op-detect: whitespace-нормализация (`gh   pr   merge`), срез git-глобалок `-c/-C X` (`git -c http.x=y merge/push`), REST-эндпоинт `gh api .../pulls/N/merge`.
- Regression: `kit/hooks/tests/test_phase_gate_canon.sh` (38 кейсов) + `test_state_integrity_security.py` (32).

## Остаток (для выделенного спринта)

**KIT-OD-1 (HIGH) — классификация по resolved argv, не по подстроке.** Подстрочный матч принципиально дыряв. Не ловятся:
- `git -c alias.z=merge z <ref>` — инлайн-алиас `z`→`merge`; резолвится только через git config, хук этого не знает.
- Произвольный `gh api` через переменную/непрямой путь к `/merge`.
- `git pull . <ref>` (fetch+merge) — гейтить весь `git pull` нельзя (ломает рутинный `git pull origin main`); нужна семантика «pull в текущую ветку = merge».

**Root-fix (auditor S61):**
1. Классифицировать по РАЗОБРАННОМУ argv: первый не-флаг токен после `git` = субкоманда (merge/pull/push); `gh` с `pr merge` ИЛИ `api` на путь `/pulls/*/merge` = merge. Резолв git-алиасов (`git config --get alias.X`) перед классификацией.
2. **Ключевать гейт от состояния ветки/диффа, а не только от строки команды** — так опечатка/непрямая форма команды не разоружает барьер. (Пересекается с S62 tamper-evidence и с идеей server-side branch protection на remote как последним рубежом.)

**KIT-OD-2 (из S61, отложено) — body-table/artifact-forgery.** phase-advance Phase-5-строка `| 5 Verify | done |` и review-gate `Blockers: 0` / review-sNN.md — markdown, который гейты grep'ают, но state_integrity НЕ валидирует. Forged-valid-backup с поддельным телом таблицы проходит. → S62 tamper-evidence (подпись/hash артефактов + commit-in-range).

## Приоритет
Money-контур защищён diff-детектом → это process-integrity, не прямой money-safety. Планировать после S62 (manifest/tamper-evidence даёт часть инфраструктуры). Не блокирует mega-run.
