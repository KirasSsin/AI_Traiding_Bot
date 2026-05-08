---
name: pydantic-v2-settings-mutability-risk
description: Pydantic v2 BaseSettings is mutable — model_validator runs ONLY at construction
type: feedback
---

**Rule:** Settings invariants enforced via `@model_validator(mode="after")` cover construction only. Any `settings.attr = value` AFTER construction silently bypasses validators in pydantic v2 unless `model_config = ConfigDict(frozen=True)` is set.

**Why:** Pydantic v2 changed validation semantics — assignment validation requires explicit `validate_assignment=True` ConfigDict option. AI Trading Bot's `Settings.model_config` (config.py:43) currently lacks both `frozen=True` AND `validate_assignment=True`.

**How to apply:**
- For money-path invariants (S35 MAINNET exclusion, live_trading guards): recommend adding `validate_assignment=True` к Settings model_config. Ensures runtime mutation re-runs validators.
- Alternative: add `frozen=True` to forbid mutation entirely. Cleaner but breaks any code that does runtime config swaps (audit needed).
- Test surface: `test_settings_s35.py` only covers construction-time validation. Need "mutation-after-construction" negative test if mutation path is plausible.
