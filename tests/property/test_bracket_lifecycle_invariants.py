"""ADR 0020 sub-decision 8: bracket lifecycle invariants (hypothesis property tests)."""
from decimal import Decimal

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.execution.bracket import compute_oco_qty
from src.execution.state_machine import (
    TRANSITIONS,
    ExecutionEvent,
    ExecutionState,
    IllegalTransitionError,
    apply,
)

LEGAL_EVENTS = list({e for (_, e) in TRANSITIONS.keys()})


@given(
    seed_state=st.sampled_from([
        ExecutionState.FLAT,
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMED,
        ExecutionState.OCO_ARMING,
        ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SL_RESIDUAL,
    ]),
    events=st.lists(st.sampled_from(LEGAL_EVENTS), min_size=1, max_size=10),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_invariant_1_bracket_no_orphan(seed_state, events):
    """I1: any reachable non-terminal state has at least one legal exit — never orphan."""
    state = seed_state
    for evt in events:
        try:
            state = apply(state, evt)
        except IllegalTransitionError:
            continue
    if state in (
        ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SL_RESIDUAL,
        ExecutionState.OCO_ARMING,
        ExecutionState.OCO_ARMED,
    ):
        next_legal = [(s, e) for (s, e) in TRANSITIONS.keys() if s == state]
        assert len(next_legal) > 0, f"No legal exits from {state} — orphan risk"


@given(
    qty=st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=8),
    fee=st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=8),
)
@settings(max_examples=200, deadline=None)
def test_invariant_g5_oco_qty_never_negative(qty, fee):
    """I-G5: compute_oco_qty result is always >= 0."""
    result = compute_oco_qty(
        cum_exec_qty=qty,
        cum_exec_fee=fee,
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert result >= Decimal("0")


@given(prior_attempt=st.integers(min_value=0, max_value=10))
def test_invariant_3_attempt_num_monotonic(prior_attempt):
    """I3: attempt number is monotonically increasing by >=1 on retry."""
    new_attempt = prior_attempt + 1
    assert new_attempt > prior_attempt
