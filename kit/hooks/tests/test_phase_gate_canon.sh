#!/usr/bin/env bash
# S61 round-4 regression: phase-gate must NOT fail-open on a non-canonical phase.
# Mirrors the exact parse+case pipeline in sprint-flow-check/phase-advance/
# review-gate. Forged unicode/zero-width/garbage phase → BLOCK (was silent ALLOW,
# disarming KIT-002 / review-gate M-2). Standalone: `bash test_phase_gate_canon.sh`.
set -u
fail=0

classify() {  # replicate the gate's canonical case arms
    local state_phase="$1"
    case "$state_phase" in
        [2-8]|[2-8]-*) echo "BLOCK-active" ;;
        ""|between-sprints|autoresearch|1|1-*|9|9-*) echo "ALLOW" ;;
        *) echo "BLOCK-noncanon" ;;
    esac
}

parse_phase() {  # replicate grep|sed used by the gates
    local raw="$1" sf; sf=$(mktemp)
    printf 'phase: %s\n' "$raw" > "$sf"
    grep -m1 '^phase:' "$sf" \
        | sed 's/^phase:[[:space:]]*//;s/[[:space:]]*#.*$//;s/[[:space:]]*$//'
    rm -f "$sf"
}

check() {  # check <label> <raw-phase> <expected-classification>
    local got; got=$(classify "$(parse_phase "$2")")
    if [ "$got" = "$3" ]; then
        printf 'PASS  %-32s -> %s\n' "$1" "$got"
    else
        printf 'FAIL  %-32s -> %s (want %s)\n' "$1" "$got" "$3"; fail=1
    fi
}

NBSP=$(printf '\xc2\xa0'); ZWSP=$(printf '\xe2\x80\x8b'); IDEO=$(printf '\xe3\x80\x80')

check "clean 4"            "4"                 "BLOCK-active"
check "clean 7-sync"       "7-sync"            "BLOCK-active"
check "clean 8-ship"       "8-ship"            "BLOCK-active"
check "between-sprints"    "between-sprints"   "ALLOW"
check "autoresearch"       "autoresearch"      "ALLOW"
check "phase 1 orient"     "1"                 "ALLOW"
check "phase 9 close"      "9"                 "ALLOW"
check "empty (no sprint)"  ""                  "ALLOW"
check "forged 4+NBSP"      "4${NBSP}"          "BLOCK-noncanon"
check "forged 4+ZWSP"      "4${ZWSP}"          "BLOCK-noncanon"
check "forged 4+ideospace" "4${IDEO}"          "BLOCK-noncanon"
check "garbage x4"         "x4"                "BLOCK-noncanon"
check "garbage 44"         "44"                "BLOCK-noncanon"


# ── round-5: command self-skip removed — decoy comment/&& can't disarm gate ──
# Mirrors the op-detect precedence: a real op is gated regardless of hook mention.
# helpers mirror the hooks: tr -s whitespace-normalize + strip git -c/-C globals +
# gh api merge-endpoint (round-6)
# S69 T9 (KIT-OD-1): op-detection resolved through lib/op_detect.py (shlex argv-
# classify), replacing the substring case-arms that false-fired on 'git merge' /
# 'gh pr merge' literals inside quoted args (commit message, grep pattern, echo).
# The harness now exercises the REAL lib the hooks call. Unparseable input →
# lib prints PARSE_ERROR and the hooks fall back to the conservative substring
# case (that fallback lives in the hooks, exercised there, not replicated here).
OPLIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/op_detect.py"
op_detect() { printf '%s' "$2" | python3 "$OPLIB" "$1" 2>/dev/null || echo PARSE_ERROR; }
op_review()  { op_detect merge "$1"; }
op_push()    { op_detect push  "$1"; }
op_merge()   { op_detect merge "$1"; }
op_commit()  { op_detect commit "$1"; }  # S69 T3: state-backup git-commit detection

ck() { local got="$2"; if [ "$got" = "$3" ]; then printf 'PASS  %-40s -> %s\n' "$1" "$got"; else printf 'FAIL  %-40s -> %s (want %s)\n' "$1" "$got" "$3"; fail=1; fi; }

ck "review clean merge"              "$(op_review 'gh pr merge x --squash')"                  "GATE"
ck "review decoy #comment"           "$(op_review 'gh pr merge x --squash # bash review-gate.sh')" "GATE"
ck "review decoy && invoke"          "$(op_review 'gh pr merge x && bash ./review-gate.sh')"  "GATE"
ck "review bare invocation"          "$(op_review 'bash ~/.claude/hooks/review-gate.sh')"     "allow"
ck "review selfcheck bash -n"        "$(op_review 'bash -n /h/review-gate.sh')"               "allow"
ck "review git merge-base plumbing"  "$(op_review 'git merge-base main HEAD')"                "skip"
ck "phase-advance clean merge"       "$(op_merge 'gh pr merge x')"                            "GATE"
ck "phase-advance decoy #comment"    "$(op_merge 'gh pr merge x # phase-advance.sh')"         "GATE"
ck "phase-advance bare invocation"   "$(op_merge 'bash ~/.claude/hooks/phase-advance.sh')"    "allow"
ck "sprint-flow clean push"          "$(op_push 'git push origin HEAD')"                      "GATE"
ck "sprint-flow decoy #comment"      "$(op_push 'git push origin HEAD # sprint-flow-check.sh')" "GATE"
ck "sprint-flow bare invocation"     "$(op_push 'bash ~/.claude/hooks/sprint-flow-check.sh')" "allow"

# round-6: whitespace-padded ops must still GATE (gh/git normalize at runtime)
ck "review gh   pr   merge (3sp)"    "$(op_review 'gh   pr   merge x')"                       "GATE"
ck "review gh pr  merge (2sp)"       "$(op_review 'gh pr  merge x')"                          "GATE"
ck "review gh<tab>pr<tab>merge"      "$(op_review "$(printf 'gh\tpr\tmerge x')")"             "GATE"
ck "phase-advance gh   pr   merge"   "$(op_merge 'gh   pr   merge x')"                        "GATE"
ck "sprint-flow git   push (3sp)"    "$(op_push 'git   push origin HEAD')"                    "GATE"

# round-6: git -c/-C global-flag prefix + gh api merge-endpoint must GATE
ck "review git -c x=y merge"         "$(op_review 'git -c http.version=HTTP/1.1 merge feature/x')" "GATE"
ck "review git -c a -c b merge"      "$(op_review 'git -c a=b -c c=d merge feature/x')"       "GATE"
ck "review gh api pulls/N/merge"     "$(op_review 'gh api -X PUT repos/o/r/pulls/1/merge')"   "GATE"
ck "review git merge-base plumbing2" "$(op_review 'git -c x=y merge-base main HEAD')"         "skip"
ck "phase-advance gh api merge"      "$(op_merge 'gh api -X PUT repos/o/r/pulls/1/merge')"    "GATE"
# S69 D1-01: локальный git merge (наш реальный ship-путь) раньше минул Phase-5 гейт
ck "phase-advance git merge --squash" "$(op_merge 'git merge --squash feature/sprint-69-gates')" "GATE"
ck "phase-advance git merge branch"  "$(op_merge 'git merge feature/sprint-69-gates')"         "GATE"
ck "phase-advance git merge-base"    "$(op_merge 'git merge-base main HEAD')"                  "skip"
ck "phase-advance git -c x=y merge"  "$(op_merge 'git -c http.version=HTTP/1.1 merge feature/x')" "GATE"
ck "sprint-flow git -c x=y push"     "$(op_push 'git -c http.version=HTTP/1.1 push origin HEAD:main')" "GATE"
# residual (known, backlogged): inline-alias expansion cannot be resolved statically
ck "residual inline-alias (backlog)" "$(op_review 'git -c alias.z=merge z feature/x')"        "allow"

# S69 T9 (KIT-OD-1): argv-classify kills quoted-literal false-fires — the substring
# detector gated every command that merely CONTAINED 'git merge'/'gh pr merge' text
# (commit msg / grep pattern / echo). These are NOT merges and must ALLOW. Real ops
# (incl. env-prefixed) still GATE — detection floor unchanged, only the ceiling narrows.
ck "falsefire commit msg literal"    "$(op_merge 'git commit -m "S69 phase-advance git merge detect"')" "allow"
ck "falsefire grep literal"          "$(op_review 'grep -rn "git merge" kit/hooks')"                     "allow"
ck "falsefire echo gh-pr-merge"      "$(op_merge 'echo "next: gh pr merge feature/x"')"                  "allow"
ck "falsefire commit gh-pr-merge"    "$(op_review 'git commit -m "wire gh pr merge gate"')"              "allow"
ck "falsefire python -c literal"     "$(op_merge 'python3 -c "x=1  # git merge"')"                       "allow"
ck "env-prefix real merge GATE"      "$(op_merge 'GIT_PAGER=cat git merge feature/x')"                   "GATE"
ck "push falsefire commit literal"   "$(op_push 'git commit -m "note: git push later"')"                 "allow"

# S69 T3 (KIT-008 state-backup): git-commit detection via argv catches the forms
# the substring '*git commit*' missed — `git -c x=y commit`, env-prefixed commit.
# commit-tree plumbing must NOT count; literal-in-echo must NOT count.
ck "commit plain GATE"               "$(op_commit 'git commit -m "x"')"                                   "GATE"
ck "commit -am GATE"                 "$(op_commit 'git commit -am "x"')"                                  "GATE"
ck "commit git -c global GATE"       "$(op_commit 'git -c user.name=x commit -m y')"                      "GATE"
ck "commit env-prefix GATE"          "$(op_commit 'GIT_AUTHOR_NAME=x git commit -m y')"                   "GATE"
ck "commit-tree plumbing not commit" "$(op_commit 'git commit-tree abc123 -m x')"                         "allow"
ck "commit falsefire echo literal"   "$(op_commit 'echo "run git commit later"')"                         "allow"

# ── S69 Phase-6 security-auditor BLOCKER: separator-attachment bypass ──
# shlex.split missed `; & | ( )` glued to a word → an op after a benign prefix
# (echo hi; git merge X) classified `allow`, defeating both money gates. The
# punctuation_chars lexer tokenizes those separators → real op still GATEs.
ck "sep semicolon glued merge"       "$(op_merge 'echo hi; git merge feature/x')"                          "GATE"
ck "sep semicolon tight merge"       "$(op_merge 'true;git merge feature/x')"                              "GATE"
ck "sep pipe glued merge"            "$(op_merge 'echo a|git merge feature/x')"                            "GATE"
ck "sep amp glued merge"             "$(op_merge 'echo a&git merge feature/x')"                            "GATE"
ck "sep subshell merge"              "$(op_merge '(git merge feature/x)')"                                 "GATE"
ck "sep semicolon gh pr merge"       "$(op_review 'echo done; gh pr merge 5')"                             "GATE"
ck "sep semicolon push"              "$(op_push 'echo hi; git push origin main')"                          "GATE"
ck "sep redirect merge"              "$(op_merge 'git merge feature/x > log.txt')"                         "GATE"
ck "eval merge body GATE"            "$(op_merge 'eval "git merge feature/x"')"                            "GATE"
ck "eval body literal → conservative GATE" "$(op_merge 'eval "echo git merge"')"                           "GATE"
ck "sh -c merge body GATE"           "$(op_merge 'bash -c "git merge feature/x"')"                          "GATE"
ck "sh -lc combined-flag GATE"       "$(op_merge 'bash -lc "git merge feature/x"')"                         "GATE"
ck "sh -ec combined-flag GATE"       "$(op_merge 'sh -ec "gh pr merge 5"')"                                 "GATE"
ck "sh -l no-c not shellexec"        "$(op_merge 'bash -l script.sh')"                                      "allow"
ck "newline separator merge GATE"    "$(op_merge "$(printf 'echo hi\ngit merge feature/x')")"               "GATE"
ck "brace group merge GATE"          "$(op_merge '{ git merge feature/x; }')"                               "GATE"
ck "backtick subst merge GATE"       "$(op_merge '`git merge feature/x`')"                                  "GATE"
# separators must NOT reintroduce false-fire on quoted literals:
ck "sep quoted literal no real op"   "$(op_merge 'echo hi; git commit -m "do git merge now"')"             "allow"
ck "sep quoted literal only"         "$(op_merge 'echo "later: git merge x"; ls')"                         "allow"
# ── python-reviewer B2: gh global flags (-R/--repo) before `pr merge` must GATE ──
ck "gh -R repo pr merge GATE"        "$(op_review 'gh -R owner/repo pr merge feature/x')"                  "GATE"
ck "gh --repo pr merge GATE"         "$(op_review 'gh --repo o/r pr merge x')"                             "GATE"
ck "gh --repo= pr merge GATE"        "$(op_review 'gh --repo=o/r pr merge x')"                             "GATE"
# ── python-reviewer B1: /merges must NOT false-positive as the /merge endpoint ──
ck "gh api pulls merges not merge"   "$(op_review 'gh api repos/o/r/pulls/1/merges')"                      "allow"
ck "gh api pulls merge query GATE"   "$(op_review 'gh api repos/o/r/pulls/1/merge?x=1')"                   "GATE"

echo "----"
if [ "$fail" -eq 0 ]; then echo "ALL PASS"; else echo "FAILURES"; fi
exit "$fail"
