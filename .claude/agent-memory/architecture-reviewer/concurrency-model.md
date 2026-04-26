---
name: Project concurrency model
description: Canonical threading model — ADR 0022 sub-decision 1, lock assignments, thread topology
type: project
---

Coordinator._lock = threading.RLock (reentrant, 8 methods, ADR 0022 sub-decision 1).
Reconciler._lock = threading.Lock (non-reentrant, ADR 0022 sub-decision 1).
RuntimeManager.run() = single main thread tick loop. pybit spawns its own WS callback thread internally.
Single-writer FSM invariant: all state mutations via Coordinator._transition(). No parallel writers.
asyncio deferred to S9+ per ADR 0022 sub-decision 1 (confirmed still deferred as of S11).

**Why:** Race condition prevention. pybit callback thread crosses into Coordinator — RLock required because coordinator may call back into itself (reentrant). Reconciler never calls itself recursively — plain Lock sufficient.
**How to apply:** Any proposal adding a second mutation path to Coordinator FSM = BLOCK. Any proposal adding asyncio without ADR = BLOCK.
