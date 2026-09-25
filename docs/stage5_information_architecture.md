# Stage 5 — Information Architecture

This document exists to separate three distinct kinds of information
in the system, before any new component (visual reasoning, Cosmos, or
otherwise) is added. Every future Stage 5 milestone should be checked
against this document rather than against intuition.

---

## 1. Raw Physical Observations

Direct sensor output. Nothing derived, nothing interpreted.

- `/scan` — full LiDAR range array (360 samples, per Milestone 2.2)
- `/camera` — RGB image, 640x480, `rgb8` (currently unused downstream
  of the sensor itself)
- `/imu` — orientation, angular velocity, linear acceleration
- `/odom` — raw pose + twist as published by `DiffDrive`
- TF tree — full transform chain, `odom -> base_footprint -> base_link
  -> {wheels, lidar_link, imu_link, camera_link}`

**Consumer:** Nav2 (costmaps, localization) and `world_state_node`
(as raw input to derive state from). Never the mission agent directly.

---

## 2. Derived Physical State

Computed from raw observations by existing deterministic code
(`world_state_node.py`). No interpretation of *meaning*, just
extraction of *facts*.

Currently published on `/world_state`:

- `position` (x, y) — from `/odom`
- `yaw` — from `/odom` orientation quaternion
- `nearest_obstacle_m` — from a fixed forward sector of `/scan`
- `path_blocked` — from `nearest_obstacle_m` vs. a fixed 1.0m threshold

**Not currently derived, though the raw data exists for it:**
- Obstacle direction (left/right/center of forward sector)
- Obstacle identity (which known object, if any)
- Robot velocity / stuck-vs-moving state
- Duration of any current state (see Section 5, temporal gap)

**Consumer:** the mission agent (via `agent_bridge_node`'s
`/world_state` subscription) and, independently, Nav2's own costmap
(which does NOT read this topic — it derives its own occupancy
directly from `/scan`).

---

## 3. Mission-Level Interpretation

The layer Stage 4 introduced. Takes derived state (and mission text)
and produces a decision that has *meaning* relative to the mission,
not just relative to physics.

Examples already implemented (`mission_agent.py`):

- "northern inspection point" -> a specific coordinate goal
- `path_blocked: true` -> WAIT, regardless of mission text

Examples NOT yet possible, because the derived state above doesn't
carry the needed information:

- "the obstacle blocking the route is new, not the known field
  boundary" (needs obstacle identity)
- "the path has been blocked for 8 seconds, likely not transient"
  (needs duration/change tracking — Milestone 5.3)
- "this looks like debris, not one of the three crop rows" (needs
  either a coordinate-based object registry or visual interpretation
  — Milestone 5.4/5.5)

**Consumer:** `agent_bridge_node`, which validates the interpretation
via `agent_contract.py` before it can reach Nav2.

---

## 4. Who Needs What (summary)

| Layer | Needs | Has today |
|---|---|---|
| Nav2 | Raw geometry (`/scan`, TF, costmaps) | Everything it needs already |
| Mission agent | Derived state + mission-relevant interpretation | Derived state only |
| Physical reasoning (future, unconfirmed) | Raw camera/scan, to produce new derived facts | N/A — does not exist yet |

---

## 5. Identified Gaps

Two gaps exist, and they are not the same problem:

### Gap A — Temporal (confirmed real, no new model needed)

The agent only ever sees the current instant. It cannot distinguish
"just became blocked" from "has been blocked for 30 seconds" from
"was blocked, now clear." This is a bookkeeping problem, addressed in
Milestone 5.3, and requires no AI.

### Gap B — Semantic / identity (real, but solution unconfirmed)

`nearest_obstacle_m` cannot distinguish *what* is being detected: one
of the three known crop-row cylinders, `obstacle_1`, or something
novel. Two candidate solutions exist and must be compared before
picking one:

1. A deterministic coordinate lookup against the known, fixed object
   registry (all objects in `agri_field.sdf` have fixed positions) —
   zero AI required.
2. Visual interpretation of the camera image (Milestone 5.4/5.5) —
   only justified if (1) cannot cover a case that actually matters,
   e.g. a genuinely novel/unregistered object.

**Decision to make in Milestone 5.4:** attempt (1) first, since it is
strictly simpler. Only pursue (2) for whatever residual case (1)
cannot solve.

---

## 6. Where Cosmos Reason2 Could and Could Not Fit

**Could fit:** an isolated interpreter, `camera image -> structured
text description`, feeding the mission agent's context. Never
downstream of `NavigateToPose`.

**Must not fit:** anywhere Nav2 already has a deterministic answer,
anywhere below the `NavigateToPose` boundary, or as a default
inclusion without a demonstrated missing capability behind it.

---

## 7. What Would Prove This Out

An experiment (Milestone 5.4) placing the robot facing each of the 4
known static objects in the world, testing whether coordinate-lookup
alone can already correctly identify each one. If yes for all 4,
Cosmos's candidate value narrows to only unregistered/novel objects —
a smaller, more honest claim than "vision reasoning for the whole
scene," and must be evaluated as exactly that narrower claim.