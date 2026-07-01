---
name: ponytail
description: Use when about to write or add code — enforce the minimal-code decision ladder (does it need to exist → already in codebase → stdlib → native feature → installed dep → one line → minimum code) before implementing. Complements the kit's YAGNI/KISS rules with a positive step-by-step algorithm. Trigger at PHASE 4 execution or any "add feature / write function / implement X" task.
---

# Ponytail — minimal-code ladder

Ported from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) v4.8.4 (MIT).
Companion to **caveman** (which compresses PROSE); ponytail compresses **CODE** — fewer lines, files, dependencies.

Core principle: **Stop at the first rung of the ladder that holds. The best code is never written.**

## The ladder (in order)

1. Does it need to exist? (YAGNI)
2. Already in codebase?
3. Stdlib covers it?
4. Native platform feature?
5. Already-installed dependency?
6. Can it be one line?
7. Minimum working code only

## Constraints

- Never simplify away input validation, error handling, security, or anything explicitly requested.
- Understand the problem fully before picking a rung.
- No unrequested abstractions, boilerplate, or design essays.
- Mark deliberate simplifications with `ponytail:` comments naming the ceiling and the upgrade path.
- Always ship one runnable check for non-trivial logic.

## Intensity

- **lite**: build it, name the lazier alternative
- **full**: enforce the ladder (default)
- **ultra**: YAGNI extremist, deletion before addition

## Output

Code first, then max three lines on what was skipped and when to add it.

---

Aligns with project `CLAUDE.md` "Минимальность изменений" / YAGNI section. Net-new over the prose rules: the **positive ordered algorithm** + the `ponytail:` marking convention. For post-hoc diff/repo over-engineering scans, use the `ponytail-audit` skill.
