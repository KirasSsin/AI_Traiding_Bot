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
norm() { printf '%s' "$1" | tr -s ' \t' ' '; }
argv() { printf '%s' "$(norm "$1")" | sed -E 's/git( -[cC] [^ ]+)+ /git /g'; }
op_review()  { local a n; a="$(argv "$1")"; n="$(norm "$1")"
  case "$a" in *"git merge-base"*|*"git merge-tree"*|*"git merge-file"*) echo skip; return;; esac
  case "$a" in *"gh pr merge"*|*"git merge "*|*"git merge") echo GATE; return;; esac
  case "$n" in *"gh api"*"pulls/"*"/merge"*) echo GATE; return;; esac
  echo allow; }
op_push()    { case "$(argv "$1")" in *"git push"*) echo GATE;; *) echo allow;; esac; }
op_merge()   { local n; n="$(norm "$1")"
  case "$n" in *"gh pr merge"*|*"gh api"*"pulls/"*"/merge"*) echo GATE;; *) echo allow;; esac; }

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
ck "sprint-flow git -c x=y push"     "$(op_push 'git -c http.version=HTTP/1.1 push origin HEAD:main')" "GATE"
# residual (known, backlogged): inline-alias expansion cannot be resolved statically
ck "residual inline-alias (backlog)" "$(op_review 'git -c alias.z=merge z feature/x')"        "allow"

echo "----"
if [ "$fail" -eq 0 ]; then echo "ALL PASS"; else echo "FAILURES"; fi
exit "$fail"
