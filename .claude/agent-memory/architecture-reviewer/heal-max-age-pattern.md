---
name: heal_max_age_seconds interval coupling — fix pattern
description: Config field expressed in wall-clock seconds couples to 1H interval. Semantic fix = heal_max_bars.
type: project
---

## The bug

`src/platform/config.py:97-102`: `heal_max_age_seconds: int = Field(default=3600, ...)`
Description says "Default = 1 bar period of v0.1 strategy (1H)".
At 15M (900s/bar): 3600s = 4 bars. Heal-check accepts 4-bar-stale position as current → silent safety bug.

## Fix pattern (recommended)

Replace `heal_max_age_seconds` (seconds constant) with `heal_max_bars: int = Field(default=1)`.
Compute `heal_max_age_seconds = settings.heal_max_bars * interval_ms // 1000` at `_cmd_run` bootstrap.
Settings remains pure (no derived computation). Zero circular dependency.
Deprecate old field with backward-compat shim for 1 sprint.

**Why:** Any wall-clock-seconds config for interval-dependent semantics couples config to TF. Bar-count semantics are TF-agnostic. ADR required for this change.
**How to apply:** Flag as Condition A2 (BLOCK merge of any 15M live-trading PR without this fix).
Operators with explicit HEAL_MAX_AGE_SECONDS=3600 in .env need migration warning in ADR.
