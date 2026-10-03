# Stage 5 — Evaluation (Milestone 5.8)

This document compares Case A (Stage 4 baseline: mission + symbolic
`/world_state` only) against Case B (Stage 5: mission + `/world_state`
+ `/vision_context`), using real evidence collected during Milestones
5.2-5.7, not projected or invented figures.

---

## 1. Decision Correctness

**Case A (symbolic only):** Fully verified in Stage 4 across 14
scenarios (valid/invalid responses, missing fields, out-of-bounds
coordinates, exceptions) -- see Stage 4 summary's safety table. All
behaved correctly.

**Case B (symbolic + vision):** Three combination cases were tested
live, end-to-end, through the real running system (not just unit
tests):

| LiDAR | Vision | Result | Verified live |
|---|---|---|---|
| blocked | agrees | WAIT, reinforcing note | Yes |
| blocked | disagrees | WAIT, disagreement noted, LiDAR wins | Yes |
| clear | cautions | NAVIGATE, caution noted | Yes |

In every case, the designed authority boundary held: **LiDAR decides
the action; vision only ever enriches the stated reason.** Vision
never overrode a LiDAR-grounded decision, confirmed, not assumed.

**Conclusion:** Case B adds no decision errors relative to Case A. The
combination logic is strictly additive to the reasoning, never a
replacement for the existing safety-critical path.

---

## 2. Valid / Invalid Structured Output Rate

**Case A:** Agent responses pass through `agent_contract.py`'s strict
validator -- type checks, action whitelist, bounds checks, named
location lookup. Every malformed/invalid case from Stage 4's safety
table was correctly rejected, with a specific reason, never a crash.

**Case B -- an honest gap found while writing this evaluation:**
`vision_context` has **no equivalent strict contract**. `_vision_note`
in `mission_agent.py` only does a soft `.get()` check for a
`description` field and silently skips enrichment if missing. This
is a reasonable choice for the mock (which is always well-formed), but
it means a real vision API's malformed output (missing fields, wrong
types) would not be caught the way a malformed mission-agent response
is -- it would just silently produce no vision note, rather than being
explicitly flagged as rejected the way `agent_contract.py` flags a bad
agent response. **This is a real design gap**, not yet a problem,
since nothing untrusted is feeding `vision_context` yet -- but worth
fixing with a `validate_vision_context()` function, mirroring
`agent_contract.py`, before any real vision model is connected.

---

## 3. Response Latency

**Case A:** Symbolic computation only. Every `mission_context_node`
and `agent_bridge_node` log timestamp shows sub-millisecond processing
between receiving `/world_state` and producing a decision.

**Case B:** `vision_context_node` runs its (mock) agent at 1 Hz, a
deliberate design choice reflecting real cost. The real-model
latencies collected during Milestone 5.4's Playground testing (not
simulated, actually measured) were:

| Model | Latency | Cost per call |
|---|---|---|
| Gemini 3.5 Flash | ~8-13s | $0.008-0.014 |
| GPT-6 Astra | ~6-8s | $0.016-0.023 |
| Claude Opus 5.5 | ~11-21s | $0.017-0.024 |
| Qwen3.8 Max | ~22-25s | token-based |

**Conclusion:** a real vision integration would be 1-2 orders of
magnitude slower than the symbolic pipeline, and genuinely costly per
call. This justifies the 1 Hz polling design (not per-frame) and rules
out vision as anything safety-critical-path-latency-sensitive --
consistent with its role as supplementary context, not a gating
check.

---

## 4. Mission Adaptation

**Case A:** Stage 4.7 added observation-only re-evaluation (log a
warning after 8s of sustained blockage, no action taken).

**Case B (Milestone 5.7):** Extended to active cancellation and
re-evaluation -- `agent_bridge_node` now stores the active goal
handle, cancels it after sustained blockage, waits for confirmed
cancellation, then re-runs `interpret_mission` with fresh context.

**Honest status:** this mechanism is implemented and code-reviewed
(matches ROS 2's documented async cancellation pattern), and was
confirmed not to regress the normal NAVIGATE->SUCCEEDED path (a full
run completed correctly with the new code in place). However, the
specific trigger condition -- sustained blockage during an active
goal -- could not be forced live in this environment (see
`known_limitations.md`). **This is recorded as implemented-but-not-
live-verified, not as a proven capability.**

---

## 5. Failure Handling

**Case A:** Fully covered by Stage 4's failure table (11 categories,
all handled correctly, node always survives).

**Case B:** `vision_context_callback` catches JSON parse failures
without blocking the mission pipeline -- a deliberate fire-and-forget
design, since vision is supplementary: a malformed or late vision
message should never stall a mission-critical decision. This is
untested against a real malformed vision payload (the mock never
produces one), but the code path exists and was reviewed.

---

## 6. Information Gained -- What Vision Actually Added

This is the core finding of Stage 5, backed by real evidence from
Milestone 5.4's five-scenario test (not assumed):

- **Object-relationship reasoning**: correctly identified a gap
  between two obstacles too narrow to pass through -- information
  `nearest_obstacle_m` (a single scalar) cannot express at all.
- **Identity without a registry**: correctly called crop-row cylinders
  "posts," distinct from obstacles, without needing the hardcoded
  `KNOWN_OBJECT` lookup `mission_context_node.py` depends on -- and
  therefore does not inherit that lookup's drift vulnerability
  (though this specific claim is a reasoned inference from the
  mechanism, not independently load-tested, since the mock doesn't
  depend on robot position at all).
- **Lateral clearance**: correctly identified a clear path around an
  off-center obstacle -- a capability the forward-sector-only LiDAR
  check structurally lacks.

**Where vision did NOT help, equally backed by evidence:**
- **Distance/urgency judgment**: 2 of 4 real models misjudged a
  distant boundary wall as an immediate blockage, in both the
  crop-row and open-field scenarios. LiDAR's `nearest_obstacle_m`
  never made this mistake in any test across this entire project.

---

## 7. Does the Added Model Improve the System?

**Nuanced, not a blanket yes/no:**

- **Yes**, for mission-level relationship and identity reasoning --
  real, reproducible evidence across 4 of 5 tested scenarios.
- **No**, for anything requiring precise distance or urgency --
  LiDAR remains strictly better and is correctly kept authoritative
  for exactly this reason.
- **Not demonstrated**, for genuine drift-independence (a reasoned
  architectural claim, not empirically load-tested) or for live
  mid-mission adaptation (5.7's mechanism, built but not live-fired).

This is why the system was deliberately built as a **hybrid**, not a
replacement: the authority boundary (Section 1) exists specifically
because the evidence does not support giving vision equal or greater
weight than LiDAR for safety-relevant judgments.

---

## 8. Carried-Forward Gaps (for future stages)

1. `vision_context` lacks a strict validation contract (`agent_contract.py`
   equivalent) -- needed before any real, untrusted vision model is
   connected.
2. Milestone 5.7's cancellation mechanism needs a scripted (not
   manual/GUI) test to be live-verified.
3. The "vision avoids registry drift" claim is architecturally sound
   but not empirically tested, since no real vision model was
   reachable this stage (Gemini blocked; see `known_limitations.md`).