---
name: Kelly phase caps and Wilson CI rule (ADR 0012 / ADR 0018)
description: 4-phase Kelly with fractional caps; Phase 3/4 must use Wilson CI lower bound as conservative p; Decimal hot path in phase_adjusted_fraction
type: project
---

4 Kelly phases (ADR 0012, amended ADR 0018):
- Phase 1: n<30 -> fixed 1%
- Phase 2: 30<=n<100 -> fixed 2%
- Phase 3: 100<=n<200 -> Quarter-Kelly (x0.25), cap 3%; Wilson 95% CI lower bound as p
- Phase 4: n>=200 -> Half-Kelly (x0.5), cap 5%; Wilson 95% CI lower bound as p

Wilson CI lower bound rule (ADR 0018 sub-decision 3): do NOT use point estimate wins/total. Use Wilson 95% CI lower bound as conservative p in Kelly formula. Code ref: src/risk/manager.py::_compute_p_b.

Decimal hot path (ADR 0018 sub-decision 6): Phase 3/4 multiply must be Decimal(str(f)) * Decimal("0.25"|"0.5"), result quantized to 1e-10. Do NOT use Decimal(str(f * 0.25)) (IEEE-754 noise). Code ref: src/risk/kelly.py::phase_adjusted_fraction.

**How to apply:** Any Kelly sizing review -- check both Wilson CI source and Decimal multiply order.
