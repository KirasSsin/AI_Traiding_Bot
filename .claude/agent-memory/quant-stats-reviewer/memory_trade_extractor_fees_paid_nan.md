---
name: trade_extractor fees_paid NaN path
description: NaN in fees_paid column propagates to Decimal('NaN'), caught by pydantic as ValidationError (not silent). S13 T5.
type: project
---

In `extract_trade_records`, `fees_paid = Decimal(str(row.get("fees_paid", 0)))`. If the DataFrame column contains a NaN float value, `str(float('nan'))` = `'nan'`, and `Decimal('nan')` = `Decimal('NaN')` (valid Python Decimal NaN, not an error yet).

However, pydantic `Field(..., ge=0)` on `TradeRecord.fees_paid` rejects `Decimal('NaN')` with `ValidationError: Input should be a finite number`. This means NaN in source data raises an explicit error rather than silently passing 0 or propagating NaN into the DSR pipeline.

**Why this matters:** The error message points to pydantic, not the extractor. Debugging is harder because the NaN origin (fees_paid column) is not surfaced. An explicit `pd.isna()` check with a descriptive `ValueError` before the Decimal cast would make the failure mode clearer.

**How to apply:** This is a non-blocking concern. If adding a NaN pre-flight guard to fees_paid, use `if pd.isna(row.get("fees_paid", 0)): raise ValueError(...)` before the Decimal cast. Sprint: S13 T5.
