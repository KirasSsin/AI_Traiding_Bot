#!/usr/bin/env bash
# skill-manifest.sh — S62 P1-MANIFEST: «скилл выстрелил» → проверяемый артефакт.
# Проверяет наличие per-phase артефактов спринта. Печатает 7-строчный манифест;
# любое расхождение → exit 1 (STOP перед тегом). Вызывать в sprint-finish Фаза 8.
#
# Usage: skill-manifest.sh <sprint-N> [<slug>]
#   sprint-N — номер спринта; slug — часть имени файлов (по умолчанию любой).
# Философия verification-before-completion применённая к самому киту: заменяем
# ненаблюдаемое «скилл загрузился» на наблюдаемое «артефакт скилла появился».
set -u

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || { echo "manifest: не git-репозиторий" >&2; exit 1; }
N="${1:-}"; SLUG="${2:-}"
[ -n "$N" ] || { echo "usage: skill-manifest.sh <sprint-N> [slug]" >&2; exit 1; }

W="$repo_root/llm-wiki/wiki/project"
fail=0
row() {  # row <phase> <ok:0/1> <detail>
    if [ "$2" = "1" ]; then printf '  ✓ %-10s %s\n' "$1" "$3"
    else printf '  ✗ %-10s %s\n' "$1" "$3"; fail=1; fi
}
have_glob() { compgen -G "$1" >/dev/null 2>&1; }

echo "── Skill-firing manifest: sprint $N ──"

# Phase 3 — план-файл
if have_glob "$W/plans/*sprint-$N-*${SLUG}*.md"; then row "3 Plan" 1 "plan-файл есть"
else row "3 Plan" 0 "нет plans/*sprint-$N-*${SLUG}*.md"; fi

# Phase 4 — коммиты спринта (эвристика: ≥1 коммит с (s$N) в диапазоне main..HEAD)
# review HIGH #2: якорим границу после $N — иначе `sprint-62` матчит `sprint-620`
# (тот же класс, что S59 substring-collision).
commits="$(git -C "$repo_root" log --oneline "main..HEAD" 2>/dev/null | grep -ciE "\(s$N\)|sprint-$N([^0-9]|$)|s$N[: ]" || true)"
if [ "${commits:-0}" -ge 1 ]; then row "4 Execute" 1 "$commits коммит(ов) спринта"
else row "4 Execute" 0 "нет коммитов с меткой s$N в main..HEAD"; fi

# Phase 5 — Phase 5 = done в SPRINT_STATE
if grep -qiE '\| *5 Verify *\| *done' "$W/SPRINT_STATE.md" 2>/dev/null; then row "5 Verify" 1 "Phase 5 = done"
else row "5 Verify" 0 "SPRINT_STATE: Phase 5 != done"; fi

# Phase 6 — review-sNN.md с Blockers: 0 + строкой ревьюера
rf="$W/reviews/review-s$N.md"
if [ -f "$rf" ] && grep -qiE 'Blockers[: ] *0' "$rf" && grep -qiE 'reviewer|architecture|security|ревьюер' "$rf"; then
    row "6 Review" 1 "review-s$N.md Blockers:0 + ревьюеры"
else row "6 Review" 0 "нет review-s$N.md с Blockers:0 + ревьюером"; fi

# Phase 7 — sync тронул components/ ИЛИ docs/ (review HIGH #1: kit-only спринт
# может не трогать components/ — Docs-Sync Gate признаёт docs/ равноправной целью).
# Ни того ни другого → advisory `·` (НЕ fail — иначе ложный STOP на kit-only спринте).
if git -C "$repo_root" diff --name-only "main..HEAD" 2>/dev/null | grep -qE 'components/|^docs/'; then
    row "7 Sync" 1 "components/ или docs/ обновлены"
else printf '  · %-10s %s\n' "7 Sync" "sync затронул только kit/hooks — проверь вручную (не блок)"; fi

# Phase 8 — sprint-NN страница
if have_glob "$W/sprints/sprint-$N-*.md"; then row "8 Ship" 1 "sprint-$N страница есть"
else row "8 Ship" 0 "нет sprints/sprint-$N-*.md"; fi

# Тег (проверяется отдельно — на момент вызова может ещё не быть)
if git -C "$repo_root" tag -l "v0.1.0-alpha.$N" | grep -q .; then row "tag" 1 "v0.1.0-alpha.$N"
else printf '  · %-10s %s\n' "tag" "v0.1.0-alpha.$N ещё не создан (норма до git tag)"; fi

echo "──"
if [ "$fail" = "0" ]; then echo "manifest: OK — все обязательные артефакты на месте"; exit 0
else echo "manifest: STOP — есть отсутствующие артефакты (см. ✗ выше)"; exit 1; fi
