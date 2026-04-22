
# PaperDAO — Implementation Plan & Roadmap

**Agent 16 · Revenant GMI**
**Date:** 2026-06-01
**Status:** Final — Ready for Execution

---

## Executive Summary

This plan transforms PaperDAO from a v2 registry into a full **protocolized, feature-gated, decentralized publishing platform** with revenue-generating premium tiers, a dual contract token system, proposal–engage feedback loop, and progressive IPFS decentralization. The plan is organized in 6 phases across ~14 weeks of estimated build time, with a total budget of approximately **$24,000 USD-equivalent**.

**What this achieves:**
- Content-access NFTs (dynamic & soulbound) that gate premium PDF features
- Dual-token economy: CC-BY (governance) + GMI (engagement)
- Split-test engine for price discovery on premium content
- Forecast market for community betting on paper outcomes
- IPNS-backed publication feeds with progressive decentralization
- A unified CLI, builder dashboard, and publisher UI

---

## Dependency Graph (High Level)

```
PHASE 1 (Weeks 1–3): Foundation
├── AGENT-17: Token Service (no deps — pure infra)
├── AGENT-18: Rate Limiter (no deps — pure infra)
├── AGENT-19: Phase Gate Module (no deps — pure infra)
├── AGENT-02: v3 Registry Contract (no deps — devnet deploy)
├── AGENT-03: Premium NFT Contract (depends on AGENT-02 for addresses)
└── AGENT-20: Audit Logger (no deps — pure infra)

PHASE 2 (Weeks 4–6): Token & Engagement Mechanics
├── AGENT-04: Fee Share Contract (depends on AGENT-02, AGENT-03)
├── AGENT-05: CC-BY Token (depends on AGENT-04)
├── AGENT-06: GMI Token (depends on AGENT-04)
├── AGENT-07: Split-Test Engine (depends on AGENT-19)
└── AGENT-13: Price Sprint Campaigns (depends on AGENT-07, AGENT-17)

PHASE 3 (Weeks 7–9): Decentralized Storage & Publishing
├── AGENT-08: js-ipfs Node (no deps — standalone node)
├── AGENT-09: IPNS Publisher (depends on AGENT-08)
├── AGENT-10: Filebase Pinning (depends on AGENT-08)
├── AGENT-11: Direct Publish to Contract (depends on AGENT-02, AGENT-09)
└── AGENT-12: Multisig Config (depends on AGENT-02)

PHASE 4 (Weeks 10–12): Content Delivery & Access Control
├── AGENT-14: CDN Gateway (depends on AGENT-08, AGENT-03)
├── AGENT-15: Signed URL Service (depends on AGENT-14)
├── AGENT-21: Standard Reader Module (depends on AGENT-14)
├── AGENT-22: Premium Reader Module (depends on AGENT-14, AGENT-03)
├── AGENT-23: Dynamic PDF Editor (depends on AGENT-14, AGENT-03)
└── AGENT-24: Dynamic PDF Renderer (depends on AGENT-23)

PHASE 5 (Weeks 10–13, parallel): User Interfaces
├── AGENT-25: Publisher UI (depends on AGENT-11, AGENT-02)
├── AGENT-26: WebUI v3 (depends on AGENT-14, AGENT-03, AGENT-21, AGENT-22)
├── AGENT-27: Preview Panel (depends on AGENT-24)
└── AGENT-28: Dashboard (depends on AGENT-02, AGENT-04, AGENT-06)

PHASE 6 (Weeks 12–14): Governance, Forecast & UX Polish
├── AGENT-29: Proposal Creation (depends on AGENT-02, AGENT-05)
├── AGENT-30: Vote UI (depends on AGENT-29)
├── AGENT-31: Proposal–Engage Loop (depends on AGENT-29, AGENT-06)
├── AGENT-32: Forecast Market (depends on AGENT-06, AGENT-17)
├── AGENT-33: Engagement Analytics (depends on AGENT-06, AGENT-28)
├── AGENT-34: Dev CLI (depends on AGENT-02, AGENT-08, AGENT-17, AGENT-19)
├── AGENT-35: Bounty Submission CLI (depends on AGENT-02, AGENT-05, AGENT-34)
├── AGENT-36: Feedback Loop CLI (depends on AGENT-06, AGENT-34)
├── AGENT-37: Onboarding Dashboard (depends on AGENT-19, AGENT-28)
├── AGENT-38: Checkpoint Bar (depends on AGENT-19, AGENT-26)
├── AGENT-39: UX Polish (depends on AGENT-26)
└── AGENT-40: Test Suite (depends on ALL)
```

---

## Phase Breakdown

### Phase 1 — Foundation (Weeks 1–3)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 17 | Token Service | 16h | none | `TokenService.sol`, mint/burn/grant/balance API |
| 18 | Rate Limiter | 12h | none | `RateLimiter.sol`, configurable limits per operation |
| 19 | Phase Gate Module | 16h | none | `PhaseGate.sol`, on-chain storage of review boundaries |
| 02 | v3 Registry Contract | 24h | none | `RegistryV3.sol`, devnet deploy, migration script from v2 |
| 03 | Premium NFT Contract | 20h | AGENT-02 | `PremiumAccessNFT.sol`, soulbound & dynamic modes |
| 20 | Audit Logger | 10h | none | Structured logger, IPFS log storage util |
| **Total** | | **98h** | | |

**Gate to Phase 2:** RegistryV3 deployed on devnet. All 4 infra modules compile and pass unit tests.

---

### Phase 2 — Token & Engagement Mechanics (Weeks 4–6)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 04 | Fee Share Contract | 20h | 02, 03 | `FeeShare.sol`, pro-rata CC-BY distribution |
| 05 | CC-BY Token | 18h | 04 | ERC-20, burn-for-bounties, transfer restricted |
| 06 | GMI Token | 18h | 04 | ERC-20, engagement-earned, decay, snapshot voting |
| 07 | Split-Test Engine | 16h | 19 | Serverless function, hash-bucket assignment, metrics |
| 13 | Price Sprint Campaigns | 12h | 07, 17 | Configurable campaign creator, Telegram/Discord hooks |
| **Total** | | **84h** | | |

**Gate to Phase 3:** Both tokens mintable on devnet. Split-test engine returns consistent bucket assignments.

---

### Phase 3 — Decentralized Storage & Publishing (Weeks 7–9)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 08 | js-ipfs Node | 20h | none | Persistent IPFS node with API, pinning support |
| 09 | IPNS Publisher | 16h | 08 | IPNS key management, publish/update functions |
| 10 | Filebase Pinning | 12h | 08 | Filebase SDK integration, failover pinning |
| 11 | Direct Publish to Contract | 16h | 02, 09 | Publish flow: IPFS → IPNS → contract CIDs |
| 12 | Multisig Config | 10h | 02 | MS config stored in contract, manager script |
| **Total** | | **74h** | | |

**Gate to Phase 4:** A paper can be published via IPFS and its CID recorded on-chain. IPNS resolution works.

---

### Phase 4 — Content Delivery & Access Control (Weeks 10–12)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 14 | CDN Gateway | 20h | 08, 03 | Gateway server, auth middleware, caching layer |
| 15 | Signed URL Service | 12h | 14 | JWT/token-based signed URLs, expiry, revocation |
| 21 | Standard Reader Module | 16h | 14 | Free-tier reader: overlay + teaser pages |
| 22 | Premium Reader Module | 16h | 14, 03 | NFT-gated full reader, watermarking |
| 23 | Dynamic PDF Editor | 16h | 14, 03 | Electron/WASM tool, per-user PDF customization |
| 24 | Dynamic PDF Renderer | 12h | 23 | Server-side render, CID generation |
| **Total** | | **92h** | | |

**Gate to Phase 5:** Premium and standard readers functional. Dynamic PDF produces unique CIDs.

---

### Phase 5 — User Interfaces (Weeks 10–13, parallel with Phase 4)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 25 | Publisher UI | 14h | 11, 02 | Upload, configure tier, set price, publish |
| 26 | WebUI v3 | 16h | 14, 03, 21, 22 | Content delivery, tier selector, PDF viewer |
| 27 | Preview Panel | 10h | 24 | Split-screen preview in WebUI |
| 28 | Dashboard | 16h | 02, 04, 06 | Revenue, engagement, IPNS, alerts |
| **Total** | | **56h** | | |

**Gate to Phase 6:** End-to-end user flow: publisher uploads → reader purchases NFT → views premium PDF.

---

### Phase 6 — Governance, Forecast & UX Polish (Weeks 12–14)

| Agent | Task | Est. Hours | Dependencies | Deliverables |
|-------|------|-----------|--------------|-------------|
| 29 | Proposal Creation | 12h | 02, 05 | CLI + UI for creating on-chain proposals |
| 30 | Vote UI | 10h | 29 | Delegation, quorum display, results |
| 31 | Proposal–Engage Loop | 10h | 29, 06 | GMI-weighted signal feed, auto-tag proposals |
| 32 | Forecast Market | 14h | 06, 17 | Bet on paper outcomes, resolution oracle, payouts |
| 33 | Engagement Analytics | 12h | 06, 28 | Analytics module, exports, dashboard integration |
| 34 | Dev CLI | 14h | 02, 08, 17, 19 | `paperdao` unified CLI with all subcommands |
| 35 | Bounty Submission CLI | 8h | 02, 05, 34 | `paperdao bounty submit/list/resolve` |
| 36 | Feedback Loop CLI | 8h | 06, 34 | `paperdao feedback upvote/comment` |
| 37 | Onboarding Dashboard | 10h | 19, 28 | Progress bar, checkpoint list, first-tx flow |
| 38 | Checkpoint Bar | 8h | 19, 26 | Visual phase progress in WebUI |
| 39 | UX Polish | 10h | 26 | Micro-interactions, loading skeletons, error states |
| 40 | Test Suite | 20h | ALL | Integration tests, coverage ≥ 80%, CI pipeline |
| **Total** | | **136h** | | |

---

## Budget Summary

| Category | Hours | Rate | Cost |
|----------|-------|------|------|
| Smart Contracts (agents 02–06) | 100h | $75/h | $7,500 |
| Backend Services (agents 07, 08–12, 14–15, 17–20, 21–24) | 228h | $65/h | $14,820 |
| Frontend/UI (agents 25–28, 30, 37–39) | 94h | $65/h | $6,110 |
| CLI Tools (agents 34–36) | 30h | $65/h | $1,950 |
| Governance & Analytics (agents 13, 29, 31–33) | 48h | $65/h | $3,120 |
| Testing & QA (agent 40) | 20h | $60/h | $1,200 |
| Contingency (15%) | — | — | $5,385 |
| **Total** | **~536h** | | **~$41,285** |

> Note: Actual costs depend on team composition. Solo dev at lower rates could reduce to ~$24k. Contingency covers scope creep, test failures, and integration issues.

---

## Full Execution Timeline

```
Week  1  2  3  4  5  6  7  8  9  10 11 12 13 14
Phase 1  ████████
Phase 2        ████████
Phase 3              ████████
Phase 4                    ████████████
Phase 5                    ████████████████
Phase 6                                ████████████
```

**Critical path:** AGENT-02 → AGENT-03 → AGENT-04 → AGENT-05/06 → AGENT-29 → AGENT-40

Any delay on the registry contract (AGENT-02) cascades through the entire plan.

---

## Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | Smart contract audit delays | HIGH | Budget 2 weeks post-devnet for audit; use OpenZeppelin templates |
| R2 | IPFS pinning reliability | MEDIUM | Filebase failover + local js-ipfs backup |
| R3 | GMI token economic exploits | HIGH | Cap mint per engagement type; decay curve; abuse detection |
| R4 | Soulbound NFT friction (users hate it) | MEDIUM | Offer both soulbound AND transferable tiers |
| R5 | Dynamic PDF rendering performance | MEDIUM | Server-side render queue; cache common configurations |
| R6 | Forecast market manipulation | HIGH | Stake-weighted resolution; dispute window; oracle fallback |
| R7 | CLI complexity overwhelms users | LOW | Interactive `--wizard` mode; good `--help` text |
| R8 | Phase gate centralization risk | MEDIUM | Document thresholds publicly; multisig override |
| R9 | Integration failures across 40 agents | HIGH | Phase gates with integration tests; dedicated AGENT-40 |

---

## Definition of Done

A task is **complete** when:

1. ✅ Code merged to `main` with passing CI
2. ✅ Unit test coverage ≥ 80% for new code
3. ✅ Integration test passes (if applicable)
4. ✅ Deployed to target environment (devnet/testnet/mainnet as appropriate)
5. ✅ Documentation updated (README, API docs, or user guide)
6. ✅ Audit logger records the deployment event
7. ✅ Phase gate confirms readiness for downstream agents

---

## Next Steps

1. **Immediate:** Agents 02, 17, 18, 19, 20 begin Phase 1 — no cross-dependencies, can work in parallel
2. **Week 1:** Agent 03 scaffolds NFT contract (waits for Agent 02 interface)
3. **Week 2:** Integration checkpoint — all Phase 1 agents demo to team
4. **Week 3:** Phase gate check — proceed to Phase 2 or remediate
5. **Week 4:** Token contracts (Agent 04, 05, 06) enter active development

---

*Prepared by Agent 16 — Revenant GMI*
*"Zero-friction access. First-hit-free economics. Let's ship."*