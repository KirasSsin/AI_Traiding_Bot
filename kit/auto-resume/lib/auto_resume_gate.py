#!/usr/bin/env python3
"""S67 Auto-Resume Gate (gate-only): решение «возобновлять ли» для desktop-тика.

Отличие от C2 (auto_resume_poll.py): claude НЕ вызывается — Desktop Scheduled
Task сам стартует свежую сессию, а этот модуль лишь печатает РОВНО ОДИН токен
решения в stdout (и всегда exit 0) плюс управляет маркером/состоянием:

    NONE    — маркера нет (заодно, под gate.lock, снимает осиротевший gate_state.json)
    WAIT    — маркер моложе AR_MIN_AGE (шанс живой сессии) или lock занят
    FOREIGN — маркер чужого репозитория (карантин foreign-<ts>.json)
    STALE   — маркер битый / bad session_id / просрочен / нет прогресса /
              first_ts-потолок кампании (карантин)
    GO      — возобновлять: маркер валиден и цикл не «застрял»

КОНТРАКТ ПОТРЕБИТЕЛЯ GO (Desktop Scheduled Task): потребитель НЕ ДОЛЖЕН
читать marker.session_id и НЕ ДОЛЖЕН передавать его в `claude --resume` —
он стартует СВЕЖУЮ desktop-сессию, делает cd в AR_REPO и продолжает с
SPRINT_STATE.next_action. marker.session_id опционален и валидируется
только-если-присутствует (defense-in-depth для любого будущего потребителя);
поэтому путь «пустой sid → GO» безопасен по контракту.

Кросс-тиковый прогресс: возобновлённая сессия снимает маркер на GO, а ts
переписывается при каждом новом лимите — по одному маркеру зацикливание не
видно. Поэтому sidecar gate_state.json {last_stamp, attempt, first_ts}:
одинаковый progress_stamp() (sha256 SPRINT_STATE + git HEAD) attempt раз
подряд при attempt >= AR_NOPROG_MAX → STALE + эскалация оператору через лог.
Плюс абсолютный wall-clock потолок кампании: first_ts ставится ОДИН раз при
первом GO (нет sidecar / после clear) и НЕ сбрасывается при смене stamp;
когда now - first_ts > AR_MAX_AGE → STALE (stale-timeout-<now>.json) —
thrashing (новый лимит переписывает ts маркера, любое касание SPRINT_STATE
меняет stamp и сбрасывает attempt) не продлевает кампанию бесконечно.

Безопасность (перенос C2): O_NOFOLLOW + санитайз control-символов для лога,
атомарные записи (tmp + os.replace) gate_state и карантина (rename), lock
gate.lock (mkdir, reclaim >2ч), симлинки state/log не разыменовываются,
полный маркер в лог не пишется. Fail-safe: main() всегда печатает один токен
и возвращает 0 — планировщик не должен падать из-за гейта.

Совместим с системным python3.9. env (имена/дефолты совпадают с C2): AR_DIR,
AR_REPO, AR_MIN_AGE, AR_MAX_AGE, AR_NOPROG_MAX.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

AR_DIR = Path(os.environ.get("AR_DIR", str(Path.home() / ".claude" / "auto-resume")))
AR_REPO = Path(os.environ.get("AR_REPO", "/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot"))
MIN_AGE = int(os.environ.get("AR_MIN_AGE", "300"))  # шанс живой сессии
MAX_AGE = int(os.environ.get("AR_MAX_AGE", str(48 * 3600)))  # 48ч → оператор
NOPROG_MAX = int(os.environ.get("AR_NOPROG_MAX", "3"))

MARKER = AR_DIR / "pending.json"
GATE_STATE = AR_DIR / "gate_state.json"
LOCK = AR_DIR / "gate.lock"
LOG = AR_DIR / "log"

_CTRL_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f\u2028\u2029]")
# session_id не обязателен (desktop стартует свою сессию), но если есть —
# defensive hex/dash-проверка как в C2 (argv-инъекция флага, LOW-1)
_SID_RE = re.compile(r"[0-9a-fA-F-]{8,64}")


def log(msg: str) -> None:
    """Append в AR_DIR/log: O_NOFOLLOW (анти-symlink) + санитайз (анти-инъекция строк)."""
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " gate " + _CTRL_RE.sub("?", msg) + "\n"
    try:
        AR_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o644)
    except OSError:
        return
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def progress_stamp() -> str:
    """Отпечаток прогресса: sha256(SPRINT_STATE) + git HEAD.

    Минимальный дубль C2 poll.py: kit/auto-resume/lib — не пакет (дефис в пути),
    гейт остаётся автономным для desktop-тика без importlib-акробатики.
    """
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
        # сиротский lock старше 2ч — снимаем (как в C2)
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


def _quarantine(name: str) -> None:
    """Атомарный карантин маркера (rename); сбой — в лог, не в crash."""
    try:
        MARKER.replace(AR_DIR / name)
    except OSError as exc:
        log(f"QUARANTINE FAIL {name}: {exc!r}")


def _load_gate_state() -> dict:
    """Чтение sidecar без разыменования симлинка; любой мусор → {}."""
    try:
        fd = os.open(GATE_STATE, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return {}
    try:
        raw = b""
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(fd)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_gate_state(data: dict) -> None:
    """Атомарная запись: tmp (O_NOFOLLOW) + os.replace — симлинк-цель не задевается."""
    tmp = AR_DIR / (GATE_STATE.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    try:
        os.write(fd, json.dumps(data, ensure_ascii=False).encode("utf-8"))
    finally:
        os.close(fd)
    os.replace(tmp, GATE_STATE)


def _clear_gate_state() -> None:
    with contextlib.suppress(OSError):
        GATE_STATE.unlink()


def _decide() -> str:
    if not MARKER.exists():
        # LOW: снятие сироты — под тем же gate.lock, что и записи тиков, иначе
        # гонка с os.replace параллельного залоченного тика (ложный сброс attempt).
        # Lock занят → пропускаем без ошибки: сирота уйдёт на следующем тике.
        if acquire_lock():
            try:
                _clear_gate_state()  # осиротевший sidecar не должен травить следующий цикл
            finally:
                with contextlib.suppress(OSError):
                    LOCK.rmdir()
        return "NONE"
    if not acquire_lock():
        return "WAIT"  # другой тик уже решает — не гонимся
    try:
        try:
            marker = json.loads(MARKER.read_text(encoding="utf-8"))
            age = time.time() - float(marker.get("ts", 0))
        except (ValueError, TypeError, AttributeError):
            # не-JSON / не-объект / кривой ts → карантин, не crash-loop (C2 LOW-3)
            _quarantine(f"stale-malformed-{int(time.time())}.json")
            log("MALFORMED marker -> карантин — нужен оператор")
            return "STALE"

        if age < MIN_AGE:
            return "WAIT"

        cwd = str(marker.get("cwd", ""))
        if Path(cwd) != AR_REPO:
            _quarantine(f"foreign-{int(float(marker.get('ts', 0)))}.json")
            log(f"FOREIGN cwd={cwd} — не наш репозиторий, маркер отложен")
            return "FOREIGN"

        sid = str(marker.get("session_id") or "")
        if sid and not _SID_RE.fullmatch(sid):
            _quarantine(f"stale-badsid-{int(time.time())}.json")
            log("BAD session_id -> карантин — нужен оператор")
            return "STALE"

        if age > MAX_AGE:
            _quarantine(f"stale-{int(float(marker.get('ts', 0)))}.json")
            log(f"ESCALATE: age={int(age)}s > {MAX_AGE}s — карантин, нужен оператор")
            return "STALE"

        gs = _load_gate_state()
        now = int(time.time())
        # C-B: абсолютный wall-clock потолок одной resume-кампании. Thrashing
        # обходит оба других счётчика (новый лимит переписывает ts маркера →
        # age не растёт; любое касание SPRINT_STATE меняет stamp → attempt
        # сбрасывается), но НЕ first_ts — он живёт с первого GO до clear.
        try:
            first_ts = float(gs.get("first_ts") or 0)
        except (TypeError, ValueError):
            first_ts = 0.0  # мусор в sidecar → потолок не применим (fail-safe)
        if first_ts and now - first_ts > MAX_AGE:
            _quarantine(f"stale-timeout-{now}.json")
            _clear_gate_state()
            log(
                f"ESCALATE: кампания идёт {int(now - first_ts)}s > {MAX_AGE}s"
                " (first_ts-потолок) — карантин, нужен оператор"
            )
            return "STALE"

        stamp = progress_stamp()
        if gs.get("last_stamp") == stamp:
            try:
                attempt = int(gs.get("attempt", 0)) + 1
            except (TypeError, ValueError):
                attempt = 1
            if attempt >= NOPROG_MAX:
                _quarantine(f"stale-noprogress-{now}.json")
                _clear_gate_state()
                log(
                    f"NOPROGRESS: stamp не менялся {attempt} тиков подряд — карантин, нужен оператор"
                )
                return "STALE"
            _write_gate_state(
                {"last_stamp": stamp, "attempt": attempt, "first_ts": gs.get("first_ts", now)}
            )
            log(f"GO (без прогресса, попытка {attempt}/{NOPROG_MAX})")
            return "GO"
        # первый проход или stamp сменился (прогресс) → счётчик с нуля
        _write_gate_state({"last_stamp": stamp, "attempt": 0, "first_ts": gs.get("first_ts", now)})
        log(f"GO session={sid[:12] or '-'} age={int(age)}s")
        return "GO"
    finally:
        with contextlib.suppress(OSError):
            LOCK.rmdir()


def main() -> int:
    """Всегда: один токен в stdout, код 0 — desktop-тик не падает из-за гейта."""
    try:
        decision = _decide()
    except Exception as exc:  # fail-safe: неожиданное → NONE (не возобновляем вслепую)
        with contextlib.suppress(Exception):
            log(f"GATE ERROR: {exc!r} — fail-safe NONE")
        decision = "NONE"
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
