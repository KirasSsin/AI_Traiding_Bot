#!/usr/bin/env python3
"""S61 Variant B: валидация + авто-восстановление SPRINT_STATE.md.

Проверяет YAML frontmatter (sprint/phase/branch присутствуют), phase из
допустимого множества, размер ≤6КБ. При повреждении (нет frontmatter / нет
обязательных полей / битый phase) — восстанавливает из последнего .backup и
логирует. Политика fail-OPEN (PRE-PLAN sub-decision 2): не дедлочить unattended
auto-resume; вернуть 0 всегда, чинить молча + WARN на stderr.

Использование: state_integrity.py <repo_root>
Выход: всегда 0. Диагностика — stderr.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# HEX-40 или HEX-7+ короткий sha; узкая валидация перед передачей в git (без shell)
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")

# raw-блок frontmatter (только реальные \n — НЕ через splitlines)
_FM_BLOCK = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# last_task_sha из СЫРОЙ физической строки; (.*) не матчит \n, но матчит \x0c/\x85
_LTS_LINE = re.compile(r"^last_task_sha:[ \t]*(.*)$", re.MULTILINE)
# control + Unicode line/vertical-space, на которые бьётся str.splitlines() —
# в легальном SPRINT_STATE их нет; наличие = parser-differential-атака.
# Разрешены только \x09 (tab) и \x0a (\n). (security-auditor bypass-hunt S61)
_DANGER = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")


def raw_last_task_sha(text: str) -> str | None:
    """Значение last_task_sha из СЫРОЙ строки frontmatter, без lenient dict-парсера.

    HIGH (bypass-hunt S61): frontmatter() режет `#.*` (даже `hex#$(curl)` без
    пробела — что реальный YAML НЕ считает комментарием) и splitlines() рвёт
    Unicode-переводы строк. Значит _SHA_RE проверял НОРМАЛИЗОВАННЫЙ токен, а в
    файл/resume-prompt утекала сырая нагрузка. Тут вырезаем ТОЛЬКО настоящий
    YAML-комментарий (пробел/таб + #), остальное валидируем как есть.
    """
    mb = _FM_BLOCK.match(text)
    if not mb:
        return None
    m = _LTS_LINE.search(mb.group(1))
    if not m:
        return None  # поле отсутствует
    return re.split(r"[ \t]#", m.group(1), maxsplit=1)[0].strip()


VALID_PHASES = re.compile(r"^(?:[1-9](?:-[a-z]+)?|between-sprints|autoresearch)$")
REQUIRED = ("sprint", "phase", "branch")
# gate-consumed поля обязаны быть каноничным ASCII (round-3/4): иначе zero-width/
# unicode-ws differential между Python-парсером и shell-гейтом (grep|sed|case).
# phase → VALID_PHASES, last_task_sha → _SHA_RE; тут sprint (цифры) и branch
# (git-legal ASCII). title — свободный текст (не gate-consumed) — не ограничиваем.
_FIELD_RE = {
    "sprint": re.compile(r"^[0-9]+$"),
    "branch": re.compile(r"^[A-Za-z0-9._/-]+$"),
}
MAX_BYTES = 6 * 1024

# управляющие символы для вырезки перед логом/stderr (LOW #6). Round-2: ВКЛЮЧАЕМ
# \x0a/\x0d/\u2028/\u2029 — иначе newline в имени бэкапа расщеплял бы лог-запись на
# две физические строки (log-injection). tab (\x09) сохраняем.
_CTRL_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f\u2028\u2029]")


def _sanitize(s: str) -> str:
    return _CTRL_RE.sub("?", s)


def frontmatter(text: str) -> dict[str, str] | None:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([a-zA-Z_]+):\s*(.*?)\s*(?:#.*)?$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip()
    return fm


def validate(text: str) -> list[str]:
    problems = []
    mb = _FM_BLOCK.match(text)
    if mb is None:
        return ["нет YAML frontmatter"]
    # bypass-hunt S61: control/Unicode-переводы строк во frontmatter = differential
    # между splitlines-парсером и сырым файлом/консьюмером → отклоняем весь state.
    if _DANGER.search(mb.group(1)):
        problems.append("control/линеразрыв-символы во frontmatter")
    # bypass-hunt round-3 (HIGH): НЕ-ASCII пробел. Python `.strip()`/`\s` считает
    # NBSP(U+00A0)/U+2000-200A/202F/205F/3000/1680 пробелом и срезает → validate
    # видит чистый `phase: 4`; но shell-гейты (grep|sed `[[:space:]]` = ASCII-only,
    # `case [2-8]`) видят `4\xa0` → glob НЕ матчит → все 3 phase-гейта падают open
    # (reopen KIT-002). Разрешаем только ASCII space/tab/newline. Generic (isspace),
    # не перечисление — устойчиво к будущим unicode-пробелам.
    if any(ch.isspace() and ch not in " \t\n" for ch in mb.group(1)):
        problems.append("не-ASCII пробел во frontmatter")
    # bypass-hunt round-2/3: наша frontmatter-схема ВСЕГДА плоская (`key: value`,
    # опц. ` #comment`). Требуем это от КАЖДОЙ непустой строки блока — иначе
    # indented/space-before-colon дубль (` last_task_sha:`, `\tphase:`) проскакивал
    # бы мимо dict-парсера, но last-wins консьюмер (yaml/LLM) читал бы payload.
    # + отклоняем любой ДУБЛЬ ключа (last_task_sha/phase smuggling).
    seen: set[str] = set()
    for ln in mb.group(1).split("\n"):
        if not ln.strip():
            continue
        km = re.match(r"^([a-zA-Z_][A-Za-z0-9_]*):(?: .*)?$", ln)
        if not km:
            problems.append("некорректная строка frontmatter (не плоский key: value)")
            continue
        if km.group(1) in seen:
            problems.append(f"дубль ключа frontmatter: {km.group(1)}")
        seen.add(km.group(1))
    fm = frontmatter(text)
    if fm is None:
        return ["нет YAML frontmatter"]
    for k in REQUIRED:
        if k not in fm or not fm[k]:
            problems.append(f"нет поля {k}")
    phase = fm.get("phase", "")
    if phase and not VALID_PHASES.match(phase):
        problems.append(f"недопустимый phase: {_sanitize(phase)!r}")
    # round-4: gate-consumed sprint/branch — строгий ASCII. Zero-width (U+200B/FEFF/
    # 2060, isspace=False → .strip() их НЕ срезает) остаётся в значении и валит
    # паттерн; isspace-пробелы уже отсечены block-guard'ом выше.
    for fld, rx in _FIELD_RE.items():
        val = fm.get(fld, "")
        if val and not rx.match(val):
            problems.append(f"недопустимый {fld}: {_sanitize(val)!r}")
    # HIGH #3 + bypass-hunt (security-auditor S61): last_task_sha уходит в
    # resume-prompt unattended-сессии (--allowedTools Bash). Берём СЫРУЮ строку
    # (raw_last_task_sha, не lenient dict — иначе `hex#$(curl)` протёк бы мимо
    # comment-strip). ВЕСЬ value обязан быть чистым hex-sha; иначе reject→restore.
    lts = raw_last_task_sha(text)
    if lts and not _SHA_RE.match(lts):
        problems.append(f"недопустимый last_task_sha: {_sanitize(lts)!r}")
    return problems


def safe_backups(backup_dir: Path) -> list[Path]:
    """Кандидаты-бэкапы, безопасные для восстановления, новейшие первыми.

    BLOCKER #1 (security-auditor S61): `glob` возвращает и симлинки, а copy
    по умолчанию следует за ними → `SPRINT_STATE.zzz.md -> ~/.aws/credentials`
    протёк бы секрет в git-tracked state. Здесь ОТСЕКАЕМ симлинки и всё, чей
    реальный путь вне backup_dir.
    MEDIUM #4: выбор по mtime (не лексикографике) — иначе `...99999999-*.md`
    залипает выбранным навсегда и ломается при перекосе часов.
    """
    try:
        bdir = backup_dir.resolve(strict=True)
    except OSError:
        return []
    out: list[tuple[float, Path]] = []
    for p in backup_dir.glob("SPRINT_STATE.*.md"):
        try:
            if "\n" in p.name or "\r" in p.name:
                continue  # round-2: newline в имени → log-injection при RESTORE-записи
            if p.is_symlink() or not p.is_file():
                continue
            if p.resolve(strict=True).parent != bdir:
                continue  # реальный файл вне каталога бэкапов — не доверяем
            out.append((p.stat().st_mtime, p))
        except OSError:
            continue
    out.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in out]


def stale_restore(repo: Path, restored_text: str) -> bool:
    """True если восстановленный state семантически устаревший.

    HIGH #1 (architecture-reviewer S61): integrity проверяет структуру, не
    свежесть. Восстановленный .backup может нести старые sprint/phase, которым
    поверят phase-advance/review-gate. Здесь: парсим last_task_sha из
    восстановленного frontmatter и проверяем `git merge-base --is-ancestor sha
    HEAD`. Не-предок (diverged/unreachable) ИЛИ sha отсутствует → считаем
    подозрительно устаревшим. Значение sha узко валидируется (_SHA_RE) до
    передачи в git — без shell, без инъекции.
    """
    sha = raw_last_task_sha(restored_text) or ""
    if not sha or not _SHA_RE.match(sha):
        return True  # нет валидной точки восстановления → не можем подтвердить свежесть
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, "HEAD"],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False  # git недоступен → fail-OPEN, не эскалируем
    return r.returncode != 0


def log(repo: Path, msg: str) -> None:
    logp = repo / "llm-wiki" / "wiki" / "project" / "state" / ".backup" / "integrity.log"
    logp.parent.mkdir(parents=True, exist_ok=True)
    # round-2 MEDIUM: O_NOFOLLOW — если integrity.log подменён симлинком наружу,
    # обычный open("a") дописывал бы атакующие строки в чужой файл (напр.
    # .git/hooks/pre-push). NOFOLLOW → open падает на симлинке → пропускаем лог.
    # msg санируется (newline в имени бэкапа больше не расщепляет запись).
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + _sanitize(msg) + "\n"
    try:
        fd = os.open(logp, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o644)
    except OSError:
        return  # симлинк/ошибка → не следуем, лог пропускаем (fail-safe)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def atomic_write(path: Path, text: str) -> None:
    """Пишем через temp+os.replace в том же каталоге.

    BLOCKER (bypass-hunt S61): если `path` подменён симлинком наружу репозитория,
    прямой write_text ПОШЁЛ БЫ по ссылке и перезаписал бы, напр., .git/hooks или
    ~/.claude/settings.json содержимым бэкапа. os.replace заменяет саму запись
    каталога (симлинк), НЕ следует за ней. Плюс атомарность против частичной
    записи. Вызов защищён предпроверкой is_symlink в main().
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state_tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def main() -> int:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    state = repo / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    backup_dir = repo / "llm-wiki" / "wiki" / "project" / "state" / ".backup"
    if not state.exists():
        return 0  # нет файла — не наша забота (fail-OPEN)

    # BLOCKER (bypass-hunt S61): state сам может быть подменён симлинком наружу
    # репо → read/write пошли бы по ссылке (чтение чужого файла как state, запись
    # бэкапа поверх произвольного файла). Отказываемся следовать, громко WARN.
    if state.is_symlink():
        log(repo, "REFUSE: SPRINT_STATE.md — симлинк, не следуем")
        print(
            "⚠️  STATE-INTEGRITY: SPRINT_STATE.md — СИМЛИНК (возможна подмена цели "
            "чтения/записи). Отказ следовать — почини вручную.",
            file=sys.stderr,
        )
        return 0

    text = state.read_text(encoding="utf-8", errors="replace")
    size = len(text.encode("utf-8"))
    problems = validate(text)

    if size > MAX_BYTES:
        print(
            f"⚠️  STATE-INTEGRITY WARN: SPRINT_STATE.md {size}Б > лимита {MAX_BYTES}Б — "
            "перенеси историю в log.md/sprint-NN.md",
            file=sys.stderr,
        )

    if not problems:
        return 0

    pretty = _sanitize("; ".join(problems))
    # HIGH #2 (security-auditor S61): НЕ ставим невалидированный бэкап. Идём от
    # новейшего к старому, читаем содержимое (safe_backups уже отсёк симлинки),
    # ВАЛИДИРУЕМ его; ставим только первый структурно-валидный. Ни один валидный
    # не найден → НЕ пишем ничего (пусть повреждение видно), а не устанавливаем
    # подделанный `| 6 Review | done |` в файл, которому верят money-гейты.
    for bk in safe_backups(backup_dir):
        try:
            cand = bk.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if validate(cand):
            continue  # этот бэкап тоже битый/подделан-невалидно — пробуем старше
        atomic_write(state, cand)  # temp+os.replace — не следует симлинку-назначению
        stale = stale_restore(repo, cand)
        tag = "STALE-RESTORE" if stale else "RESTORE"
        log(repo, f"{tag} from {_sanitize(bk.name)}: {pretty}")
        if stale:
            print(
                f"⚠️  STATE-INTEGRITY STALE-RESTORE WARN: SPRINT_STATE.md повреждён "
                f"({pretty}) → восстановлен из {_sanitize(bk.name)}, но его "
                "last_task_sha НЕ предок HEAD (возможно устаревший/подделанный "
                "sprint/phase). phase-advance/review-gate могут поверить старому "
                "состоянию — СВЕРЬ вручную перед merge.",
                file=sys.stderr,
            )
        else:
            print(
                f"⚠️  STATE-INTEGRITY: SPRINT_STATE.md повреждён ({pretty}) "
                f"→ восстановлен из {_sanitize(bk.name)}. Проверь корректность.",
                file=sys.stderr,
            )
        return 0

    # ни одного валидного бэкапа: не трогаем файл, повреждение остаётся видимым
    log(repo, f"CORRUPT no-valid-backup: {pretty}")
    print(
        f"⚠️  STATE-INTEGRITY: SPRINT_STATE.md повреждён ({pretty}), "
        "валидных бэкапов нет — файл НЕ перезаписан, почини вручную.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
