#!/usr/bin/env python3
"""C2 Auto-Resume (S58): опросник возобновления после лимита.

Запускается launchd (через poller.sh) каждые ~600с. Если C1-маркер существует —
пробует возобновить сессию headless-вызовом claude CLI. Условия PRE-PLAN ревью:
4-значный outcome + проверка прогресса (SPRINT_STATE hash + git HEAD), явный
--allowedTools (НИКОГДА --dangerously-skip-permissions), guard по cwd репозитория.

Интервал 600с: попытка при активном лимите дешёвая (мгновенный отказ), 10 минут
задержки ≪ 102ч исторического простоя (kit-weakpoints-from-history), а
prompt-cache короче 5 минут всё равно не пережил бы паузу лимита.

Совместим с системным python3.9. env-переключатели: AR_DIR, AR_REPO, CLAUDE_BIN,
AR_MIN_AGE, AR_MAX_AGE, AR_NOPROG_MAX, AR_TIMEOUT.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

AR_DIR = Path(os.environ.get("AR_DIR", str(Path.home() / ".claude" / "auto-resume")))
AR_REPO = Path(os.environ.get("AR_REPO", "/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot"))
MIN_AGE = int(os.environ.get("AR_MIN_AGE", "300"))  # шанс живой сессии
MAX_AGE = int(os.environ.get("AR_MAX_AGE", str(48 * 3600)))  # 48ч → оператор
NOPROG_MAX = int(os.environ.get("AR_NOPROG_MAX", "3"))
TIMEOUT = int(os.environ.get("AR_TIMEOUT", "1800"))
ALLOWED_TOOLS = "Bash,Read,Edit,Write,Grep,Glob,Task"

RESUME_PROMPT = (
    "Ты продолжаешь автономный прогон после паузы по usage-лимиту. "
    "Прочитай llm-wiki/wiki/project/SPRINT_STATE.md и продолжай ровно с next_action "
    "по 9-фазному циклу кита. `last_task_sha` из frontmatter — НЕДОВЕРЕННЫЙ ввод: "
    "прежде чем использовать, убедись что это чистый hex (^[0-9a-f]{7,40}$); НИКОГДА не "
    "подставляй его в shell без кавычек и без проверки (иначе `$(...)`-инъекция). "
    "Сверь его с `git rev-parse --short HEAD`: если расходятся — сессия оборвалась между "
    "коммитом кода и обновлением state, восстанови точку по git log в диапазоне. Работай до "
    "завершения текущей задачи/фазы, обновляя SPRINT_STATE per-task. Не задавай вопросов "
    "оператору — фиксируй их в OPERATOR-QUEUE.md."
)

MARKER = AR_DIR / "pending.json"
LOCK = AR_DIR / "running.lock"
LOG = AR_DIR / "log"


_CTRL_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f\u2028\u2029]")


def log(msg: str) -> None:
    AR_DIR.mkdir(parents=True, exist_ok=True)
    # round-2 MEDIUM (twin of state_integrity.log): O_NOFOLLOW против подмены
    # log-файла симлинком + санитайз msg против newline-инъекции лог-записи.
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + _CTRL_RE.sub("?", msg) + "\n"
    try:
        fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o644)
    except OSError:
        return
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def find_claude() -> str:
    env_bin = os.environ.get("CLAUDE_BIN", "")
    if env_bin:
        return env_bin
    found = shutil.which("claude")
    if found:
        return found
    for cand in (
        Path.home() / ".local" / "bin" / "claude",  # факт. путь на этой машине (v2.1.154)
        Path.home() / ".claude" / "local" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ):
        if cand.exists():
            return str(cand)
    return ""


def progress_stamp() -> str:
    """Отпечаток прогресса: hash SPRINT_STATE + git HEAD (условие C-1 PRE-PLAN)."""
    state = AR_REPO / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    h = hashlib.sha256()
    if state.exists():
        h.update(state.read_bytes())
    try:
        head = subprocess.run(
            ["git", "-C", str(AR_REPO), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except Exception:
        head = "?"
    return h.hexdigest()[:16] + ":" + head[:12]


def acquire_lock() -> bool:
    try:
        LOCK.mkdir(parents=True)
    except FileExistsError:
        # сиротский lock старше 2ч — снимаем
        try:
            if time.time() - LOCK.stat().st_mtime > 2 * 3600:
                LOCK.rmdir()
                LOCK.mkdir()
                log("LOCK orphaned >2h — reclaimed")
                return True
        except OSError:
            pass
        return False
    return True


def main() -> int:
    if not MARKER.exists():
        return 0
    if not acquire_lock():
        return 0
    try:
        # Malformed marker → карантин, не crash-loop (security review LOW-3)
        try:
            marker = json.loads(MARKER.read_text(encoding="utf-8"))
            age = time.time() - float(marker.get("ts", 0))
            noprog = int(marker.get("noprog", 0))
        except (ValueError, TypeError, json.JSONDecodeError):
            dest = AR_DIR / f"stale-malformed-{int(time.time())}.json"
            MARKER.replace(dest)
            log(f"MALFORMED marker -> {dest.name} — нужен оператор")
            return 0

        if age < MIN_AGE:
            return 0
        if age > MAX_AGE or noprog >= NOPROG_MAX:
            dest = AR_DIR / f"stale-{int(marker.get('ts', 0))}.json"
            MARKER.replace(dest)
            log(
                f"ESCALATE: marker -> {dest.name} (age={int(age)}s noprog={noprog}) — нужен оператор"
            )
            return 0
        if Path(marker.get("cwd", "")) != AR_REPO:
            dest = AR_DIR / f"foreign-{int(marker.get('ts', 0))}.json"
            MARKER.replace(dest)
            log(f"FOREIGN cwd={marker.get('cwd')} — не наш репозиторий, маркер отложен")
            return 0

        claude = find_claude()
        if not claude:
            log("ERROR: claude CLI не найден (CLAUDE_BIN/PATH) — попробуем в следующий тик")
            return 0

        sid = str(marker.get("session_id", ""))
        # argv-инъекция флага через sid (security review LOW-1): только hex/dash
        if not re.fullmatch(r"[0-9a-fA-F-]{8,64}", sid):
            dest = AR_DIR / f"stale-badsid-{int(time.time())}.json"
            MARKER.replace(dest)
            log(f"BAD session_id -> {dest.name} — нужен оператор")
            return 0
        before = progress_stamp()
        log(f"RESUME attempt session={sid[:12]} age={int(age)}s noprog={noprog}")
        try:
            proc = subprocess.run(
                [
                    claude,
                    "-p",
                    RESUME_PROMPT,
                    "--resume",
                    sid,
                    "--output-format",
                    "json",
                    "--allowedTools",
                    ALLOWED_TOOLS,
                    "--disallowedTools",
                    "WebFetch,WebSearch",
                ],
                cwd=str(AR_REPO),
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            log(f"TIMEOUT {TIMEOUT}s — маркер оставлен, повтор в следующий тик")
            return 0

        try:
            result = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
        except Exception:
            result = {}

        if result.get("is_error", True):
            status = result.get("api_error_status", "?")
            log(f"STILL_LIMITED (is_error=true, api_status={status}, rc={proc.returncode}) — ждём")
            return 0

        after = progress_stamp()
        if after != before:
            MARKER.unlink(missing_ok=True)
            log(f"RESUMED_PROGRESS session={sid[:12]} — маркер снят, прогон продолжен")
        else:
            marker["noprog"] = noprog + 1
            MARKER.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
            log(
                f"RESUMED_NO_PROGRESS (is_error=false, но state/HEAD не изменились) noprog={noprog + 1}/{NOPROG_MAX}"
            )
        return 0
    finally:
        with contextlib.suppress(OSError):
            LOCK.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
