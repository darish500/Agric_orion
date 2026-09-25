# Agri-ORION — Stage 4 Summary

**Project:** Agri-ORION — Nebius × NVIDIA Global AI Hackathon 2026, Physical AI track
**Stage:** 4 of the 20-day plan — Agentic Mission Reasoning & AI–Robot Interface
**Status:** Core architecture complete and fully verified with a mocked agent.
Live Nemotron connection (Milestone 4.2) blocked on a Nebius billing-country
limitation, actively escalated.
**Environment:** Ubuntu, ROS 2 Jazzy, Gazebo Harmonic, Nav2, Nebius Token Factory (OpenAI-compatible API)

---

## 1. What Stage 4 Set Out To Do

Introduce the first AI reasoning layer -- NVIDIA Nemotron via Nebius Token
Factory -- strictly **above** the deterministic Stage 1-3 stack, converting
open-ended human missions into structured, validated navigation objectives.
The single non-negotiable rule carried through every milestone: **the
foundation model may only ever produce a high-level objective; it must
never touch `/cmd_vel`, velocity, or any safety-critical motion.**

The stage deliberately began with the *contract* between the AI and the
robot -- not with API integration -- so the entire deterministic safety
boundary could be built and proven before any nondeterministic model
output ever entered the system.

---

## 2. Architecture Achieved

```
Human mission (text)
        |
Mock Nemotron Agent  <-- world_state (position, yaw, nearest_obstacle_m,
        |                  path_blocked) from existing Stage 2 node
        v
Structured response: {action, target, reason}
        |
Deterministic Validator (agent_contract.py)
   - type/shape checks
   - action whitelist
   - named-location lookup (trusted table) OR
     raw x/y bounds check (explicit map extent)
   - never raises, always returns (True, obj) / (False, reason)
        |
   [REJECTED] -----------------> nothing sent, logged, node keeps running
        |
   [valid, WAIT] --------------> nothing sent, logged as a legitimate
        |                        mission-level decision
   [valid, NAVIGATE]
        |
        v
NavigateToPose action call (ROS 2 action, not topic/service --
goal/feedback/result three-part contract)
        |
        v
Stage 3 Nav2 stack (bt_navigator -> planner_server -> controller_server)
        |
        v
Stage 1 DiffDrive plugin -> vehicle -> Stage 2 sensors -> world_state
        |
        +--> fed back into the agent's next decision (closed loop)
```

`world_state_node.py` was never modified -- exactly as instructed, it
retains its distinct role ("what do we currently know") separate from
Nav2's own costmaps ("what can I safely drive through").

---

## 3. Milestone Status

### 4.1 -- Agent contract & validation (COMPLETE)
Built `agent_contract.py`: a pure-Python, network-free, ROS-free
validator. Deliberately designed before any model connection so its
correctness could be proven in milliseconds against hand-written inputs.
Supports two ways of specifying a NAVIGATE target -- a name from a
pre-vetted `KNOWN_LOCATIONS` table (trusted by construction, no bounds
check needed) or raw `x`/`y` (explicitly bounds-checked against the real
map extent from `generate_map.py`). Never raises an exception; always
returns `(bool, result_or_reason)`.

### 4.2 -- Nebius Token Factory connection (BLOCKED, escalated)
Confirmed Nebius Token Factory is an OpenAI-compatible API
(`base_url="https://api.tokenfactory.nebius.com/v1/"`), with current
Nemotron model IDs including `nvidia/nemotron-3-super-120b-a12b`. A real
gotcha was identified before implementation: Nemotron models on this
platform can return their answer in a separate `reasoning_content`
field rather than `content`, requiring the client code to check both.

Blocked: Nebius account signup requires a billing country, and Nigeria
is not currently supported (confirmed directly by Nebius Support, who
have raised an internal request with no committed timeline). A hackathon
promo-credit path (activation code `NEBIUS-DEVPOST-GLOBAL26`) was tried
as an alternative but hits the same underlying billing-country gap.
Escalated via email to both Nebius Support and the hackathon organizer
(Devpost), explicitly citing the hackathon's own stated eligibility
("all countries/territories, excluding standard exceptions"). Awaiting
resolution.

**Decision:** proceed with a clearly-labeled `MockNemotronAgent`,
per the project brief's own explicit allowance for this during interface
development, and build every downstream milestone against it. Real
integration point is a single, well-isolated swap (see Section 6).

### 4.3 -- Mock mission reasoning (COMPLETE)
Built `mission_agent.py` (`MockNemotronAgent`) and
`mission_reasoning_test.py`. Verified five distinct outcomes from a
single pipeline: valid mission, ambiguous mission (plausible but unknown
location), unsupported/hallucinated coordinates (out of map bounds),
irrelevant request (unsupported action), and a mission with no matching
response at all. Every case produced the correct, specific
accept/reject result.

Real bug found and fixed: `interpret_mission`'s key-normalization
(`.strip().lower()`) did not initially strip trailing punctuation,
causing every test mission (which include periods/question marks) to
silently miss its dictionary entry -- a genuinely realistic class of
bug relevant to real model output framing, not just a toy mistake.

### 4.4 -- World-state integration (COMPLETE)
Extended `MockNemotronAgent` to read `world_state` and make a
world-aware decision **before** consulting the mission-text table: if
`path_blocked` is `True`, the agent returns `WAIT` regardless of what
the mission asked for. Verified directly: the identical mission text
("Go to the northern inspection point") produced two different, both
valid outcomes (`NAVIGATE` vs `WAIT`) purely based on world state --
concrete proof that physical context genuinely participates in the
decision at the mission level, not the motor level.

### 4.5 -- Agent to validated NavigateToPose (COMPLETE)
Built `agent_bridge_node.py`: subscribes to the real `/world_state`
topic, calls the agent, validates the response, and -- only if valid
and `NAVIGATE` -- sends a real `NavigateToPose` action goal via
`ActionClient`, using the standard three-part action pattern (goal
response / feedback / result callbacks). Concept of *why* an action
(not a topic or service) is the correct interface for this was taught
and understood before implementation: long-running, monitorable,
cancellable work is exactly what actions exist for.

Verified end to end with a genuine, complete drive: `distance_remaining`
decreasing smoothly and continuously from 3.00m to arrival over ~27
real seconds, `SUCCEEDED` result -- not a coincidental "already there"
result (an earlier false-positive run was correctly identified and
re-tested after a stray duplicate `static_transform_publisher` process
was found and killed).

### 4.6 -- First end-to-end agentic mission (COMPLETE)
The Milestone 4.5 verified run stands as the complete artifact: human
mission text -> mock agent response -> validated objective ->
`NavigateToPose` goal -> Nav2 execution -> real robot arrival ->
`SUCCEEDED`, entirely without manual `/cmd_vel`.

### 4.7 -- Closed-loop context (COMPLETE)
Added a 2-second re-evaluation timer to `agent_bridge_node.py`,
independent of Nav2's own control loop, that tracks how long
`path_blocked` has been continuously `True` during an active goal
(resetting on any clear, so only sustained blockage counts). Two
distinct closed-loop behaviors were verified with real evidence:

1. **Mid-mission re-evaluation:** a genuinely stuck robot
   (`recoveries=6`, `distance_remaining` frozen at 7.40m) triggered a
   `[AGENT RE-EVAL]` warning after 16.0 seconds of sustained blockage --
   proof the agent independently monitors mission-level health on its
   own schedule, without touching Nav2's own recovery attempts.
2. **Pre-mission check:** stale `path_blocked: True` world state at
   startup caused the very first mission decision to resolve to `WAIT`
   instead of `NAVIGATE`, before any goal was ever sent -- the
   "should I even act" check working at the earliest possible point.

This milestone deliberately stopped at observation-only, per the
project's own risk-averse default: intervention (cancel + replan) is a
well-justified future increment once real threshold data exists, not a
guess made without evidence.

### 4.8 -- Failure and safety testing (COMPLETE)
Consolidated every failure category from the original brief, with real
collected evidence for each (see table below). The one genuinely new
case this milestone added: a simulated raised exception (`ConnectionError`)
from the agent call, standing in for a real API timeout/network failure
-- a fundamentally different failure *shape* than a bad return value.
Found and fixed a real gap: `run_mission` had no `try/except` around the
agent call, meaning a real API exception would have propagated
uncaught. Added exception handling; verified the node logs the failure,
sends nothing to Nav2, and **remains running** afterward, confirmed via
`ros2 node list`.

---

## 4. Safety / Failure Evidence Table

| Failure category | Verified outcome |
|---|---|
| Not valid JSON / not a dict | Rejected, specific reason, no crash |
| Missing `action` field | Rejected, specific reason |
| Unsupported action | Rejected, specific reason |
| `target` missing both `location` and `x`/`y` | Rejected, specific reason |
| `x`/`y` wrong type (string, bool) | Rejected, specific reason |
| `x`/`y` outside map bounds | Rejected, specific reason |
| Unknown `location` name | Rejected, specific reason |
| No matching mission at all | Rejected (empty response -> missing action) |
| Sustained physical blockage mid-mission | Logged, observed, Nav2 continues its own recovery |
| World already blocked at mission start | `WAIT` chosen before any goal sent |
| Agent call raises an exception | Caught, logged, nothing sent, node survives |

In every single case: **the deterministic layer either executes a
validated objective or does nothing physical at all.** No partial
execution, no best-guess fallback, no crash.

---

## 5. Real Bugs Found and Fixed This Stage

- Key-normalization mismatch in `interpret_mission` (trailing
  punctuation not stripped) -- silent, total lookup failure across
  every test case until diagnosed via the uniform, identical rejection
  reason across all of them.
- Missing `try/except` around the agent call in `run_mission` --
  a real robustness gap that would have let a genuine API failure
  crash or destabilize the node.
- A stray duplicate `static_transform_publisher` process (carried over
  from Stage 3's known pattern of orphaned processes) caused one
  `NavigateToPose` test to report a misleadingly instant `SUCCEEDED` --
  correctly diagnosed via `ros2 node list`'s own duplicate-name warning
  before drawing false conclusions about the pipeline.

---

## 6. Completing Milestone 4.2 Once Nebius Access Is Available

The integration point is a single, isolated swap. A real
`NemotronAgent` class needs only to implement the identical method
signature already used everywhere else in the system:

```python
def interpret_mission(self, mission_text, world_state=None):
    # 1. Build a prompt including mission_text, world_state, and the
    #    KNOWN_LOCATIONS table (so the model selects from safe, named
    #    options rather than inventing coordinates).
    # 2. Call client.chat.completions.create(...) against
    #    https://api.tokenfactory.nebius.com/v1/ with the API key from
    #    an environment variable (NEBIUS_API_KEY) -- never hardcoded.
    # 3. Check BOTH response.choices[0].message.content and
    #    .reasoning_content -- Nemotron models on this platform can
    #    return either.
    # 4. Parse the result as JSON. If parsing fails, return {} (the
    #    existing "no match" fallback already handles this safely).
    # 5. Return the parsed dict in the exact same shape MockNemotronAgent
    #    produces.
```

Everything downstream -- `agent_contract.py`'s validation,
`agent_bridge_node.py`'s Nav2 bridge, the closed-loop re-evaluation
timer, and every safety/failure path in Section 4 -- requires **no
changes at all**. Swapping `self.agent = MockNemotronAgent()` for
`self.agent = NemotronAgent()` in `agent_bridge_node.py` is the entire
remaining integration step.

---

## 7. What Stage 4 Deliberately Did Not Include

Per original scope: no Cosmos Reason2, no Isaac GR00T, no YOLO, no
SLAM, no reinforcement learning, no custom AI planner, no multi-agent
system, no LLM-generated ROS commands, no `ros2_control`. The agent
never once touched `/cmd_vel` or any topic below the `NavigateToPose`
action boundary, at any point in this stage.

---

## 8. Progress Checklist (cumulative)

- [x] Stage 1 -- ROS 2 + Gazebo robotics foundation
- [x] Stage 2 -- Perception layer
- [x] Stage 3 -- Deterministic navigation baseline
- [x] Stage 4 -- Agentic mission reasoning architecture (mock-verified)
- [ ] Stage 4.2 live completion -- pending Nebius billing-country resolution
- [ ] Stage 5 -- not yet scoped