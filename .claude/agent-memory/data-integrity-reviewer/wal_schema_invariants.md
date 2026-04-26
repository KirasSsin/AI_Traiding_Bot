---
name: WAL + Schema invariants
description: Canonical SQLite connection pragmas, Decimal-as-TEXT rule, and migration forward-only rules for this project
type: project
---

WAL mode asserted at connect: `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;`.

Decimal monetary values stored as TEXT (str(Decimal)) never REAL — IEEE precision loss prevention. Pattern consistent across trade_history.py, fill_history.py, state_repo.py.

Migrations: forward-only in migrations/. Runner tracks applied versions in schema_version table. Files named NNNN_<slug>.sql. Re-run is a no-op (IF NOT EXISTS / ALTER IF NOT EXISTS pattern).

**Why:** Verified through S4-S12 migrations. SQLite REAL = 64-bit float = silent precision loss for price/qty. TEXT+Decimal = exact arithmetic in domain models.

**How to apply:** Flag any column storing price/qty/fee as REAL as a blocker. Flag any modification of an existing migration file as a blocker.
