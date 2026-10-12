# Stage 6 run records

Companion to `stage6_evaluation.md` (section 3.5 and 3.6). These are the live closed-loop runs in
Gazebo, with the field-centre goal at (0, 0) and a scripted 0.15 m box appearing ahead of the robot
while it is driving.

## How to read this file

- **Evidence note.** The raw terminal logs were not written to files (the target folder did not
  exist). The excerpts below were transcribed from the terminal output captured at the time.
- **Shortened for readability.** ROS timestamp prefixes and node names are removed, the repeated
  `NAV2 FEEDBACK` lines are reduced to a few samples, and the long mock-vision sentence inside
  `reason` fields is shortened to `…`. Every other character is as printed.
- **Times** in the timelines are seconds after the first `Nav2 accepted the goal`, computed from the
  original log timestamps.
- **Clearance** is the gap between the robot's front and the box's near face at the moment the
  robot stopped, computed as `(box_x - 0.1) - (robot_x + 0.2)`. The 0.4 m body length comes from the
  xacro; the box is 0.2 m deep. The robot position is Nav2's "begin navigating from current
  location" pose at the moment of resume. The `clearance.py` readings taken after each trial are
  not used, because they were measured after the run had finished.
- The goal is the field centre (0, 0); the robot starts at (-3, 0) and drives east.

## Summary

| Run | OpenCV | Box spawned (robot x to box x) | Guard ranges | Stop clearance | Nav2 result |
|---|---|---|---|---|---|
| B1 | on | -1.51 to -0.01 | 1.05, 0.90 m | 0.59 m | CANCELED, then SUCCEEDED |
| B2 | on | -2.59 to -1.09 | 1.11, 0.89 m | 0.64 m | CANCELED, then SUCCEEDED |
| B3 | on | not recorded | 1.13, 1.04 m | not recorded | CANCELED, then SUCCEEDED |
| A1 | off | -2.43 to -0.93 | none | contact (observed) | SUCCEEDED while stuck |
| A2 | off | -2.45 to -0.95 | none | contact (observed) | SUCCEEDED while stuck |
| A3 | off | -1.70 to -0.20 (late) | none | contact (observed) | SUCCEEDED while stuck |
| V1 | off | -2.61 to -1.11 | none | 0.03 m (Gazebo pose) | SUCCEEDED while stuck |

B = OpenCV evidence on (`use_visual_evidence:=true`). A = off (`false`). V1 is the verification run
that read the robot's true pose from Gazebo.

---

## B1: OpenCV on

**Command**

```bash
ros2 run agric_orion agent_bridge_node --ros-args \
  -p mission:="Go to the field centre." -p use_visual_evidence:=true
```

**Setup:** box spawned when the robot was at world (-1.51, 0.00); box centre (-0.01, 0.00), near face -0.11.

**Result:** stopped before the box. Resume pose (-0.90, 0.00), front at -0.70, **clearance 0.59 m**.
After the box was removed the mission resumed and finished SUCCEEDED.

| t (s) | Event |
|---|---|
| 0.00 | Nav2 accepted the goal (distance 2.60 m two seconds later) |
| 9.85 | `VISION GUARD` hit 1 of 2, range 1.05 m |
| 10.88 | hit 2 of 2, range 0.90 m; cancel issued |
| 10.89 | Nav2 confirmed the cancel (4.8 ms after the decision) |
| 10.91 | goal finished CANCELED; agent had chosen WAIT |
| 43.25 | box removed earlier; three clear results, mission re-run, NAVIGATE |
| 47.51 | goal finished SUCCEEDED |

**Bridge log (excerpt)**

```text
[AGENT BRIDGE] Mission: "Go to the field centre."
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0, 'n_components': 0, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.7, 'round_trip_ms': 802.7, 'timestamp': 1791587897.8971224, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[VALIDATOR] valid=True -> {'action': 'NAVIGATE', 'x': 0.0, 'y': 0.0, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.60m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.82m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.45m, recoveries=0
[VISION GUARD] obstruction seen (1/2), range ~1.05 m
[NAV2 FEEDBACK] distance_remaining=1.07m, recoveries=0
[VISION GUARD] obstruction seen (2/2), range ~0.9 m
[AGENT RE-EVAL] OpenCV reports an obstruction during an active goal -- cancelling the goal to re-evaluate the mission.
[AGENT RE-EVAL] Nav2 confirmed the goal was cancelled. Re-evaluating mission with current context.
[AGENT BRIDGE] Mission: "Go to the field centre."
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': True, 'corridor_occupancy': 0.1659, 'n_components': 1, 'largest_px': 6816, 'lateral_bin': 'center', 'est_range_m': 0.9, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.8, 'round_trip_ms': 1020.8, 'timestamp': 1791587908.6464186, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports an obstruction in the forward corridor (range ~0.9 m, lateral=center, occupancy=0.1659); holding off on issuing a new navigation objective.'}
[VALIDATOR] valid=True -> {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports …'}
[AGENT BRIDGE] Agent chose WAIT, nothing sent to Nav2. Reason: LiDAR path_blocked is False, but OpenCV visual evidence reports …
[AGENT BRIDGE] Nav2 goal finished: CANCELED
[VISION GUARD] obstruction at ~2.18 m is explained by LiDAR (nearest 2.25 m); not adding a stop.
[AGENT RE-EVAL] OpenCV evidence has been clear again -- re-running the mission.
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0086, 'n_components': 1, 'largest_px': 352, 'lateral_bin': 'center', 'est_range_m': 2.18, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 10.5, 'round_trip_ms': 753.1, 'timestamp': 1791587941.2874415, 'backend': 'url', 'note': 'obstruction explained by LiDAR'}
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[VALIDATOR] valid=True -> {'action': 'NAVIGATE', 'x': 0.0, 'y': 0.0, 'reason': '…'}
[AGENT BRIDGE] Nav2 accepted the goal.
[VISION GUARD] obstruction at ~1.8 m is explained by LiDAR (nearest 1.70 m); not adding a stop.
[NAV2 FEEDBACK] distance_remaining=0.27m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

**Nav2 server log (excerpt)**

```text
[bt_navigator]: Begin navigating from current location (-3.00, 0.00) to (0.00, 0.00)
[controller_server]: Cancellation was successful. Stopping the robot.
[bt_navigator]: Begin navigating from current location (-0.90, 0.00) to (0.00, 0.00)
[controller_server]: Reached the goal!
[bt_navigator]: Goal succeeded
```

---

## B2: OpenCV on

**Setup:** robot at world (-2.59, 0.00) when the box was spawned; box centre (-1.09, 0.00), near face -1.19.

**Result:** stopped before the box. Resume pose (-2.03, 0.00), front at -1.83, **clearance 0.64 m**.
Mission resumed after the box was removed and finished SUCCEEDED.

| t (s) | Event |
|---|---|
| 0.00 | Nav2 accepted the goal |
| 4.41 | `VISION GUARD` hit 1 of 2, range 1.11 m |
| 5.23 | hit 2 of 2, range 0.89 m; cancel issued |
| 5.23 | Nav2 confirmed the cancel (3.2 ms after the decision) |
| 5.26 | goal finished CANCELED; agent had chosen WAIT |
| 104.25 | box removed earlier; three clear results, mission re-run, NAVIGATE |
| 114.35 | goal finished SUCCEEDED |

**Bridge log (excerpt)**

```text
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0, 'n_components': 0, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.6, 'round_trip_ms': 724.8, 'timestamp': 1791588256.6951325, 'backend': 'url'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.62m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=2.27m, recoveries=0
[VISION GUARD] obstruction seen (1/2), range ~1.11 m
[VISION GUARD] obstruction seen (2/2), range ~0.89 m
[AGENT RE-EVAL] OpenCV reports an obstruction during an active goal -- cancelling the goal to re-evaluate the mission.
[AGENT RE-EVAL] Nav2 confirmed the goal was cancelled. Re-evaluating mission with current context.
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': True, 'corridor_occupancy': 0.1702, 'n_components': 1, 'largest_px': 6992, 'lateral_bin': 'center', 'est_range_m': 0.89, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.7, 'round_trip_ms': 812.0, 'timestamp': 1791588261.9281585, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports an obstruction in the forward corridor (range ~0.89 m, lateral=center, occupancy=0.1702); holding off on issuing a new navigation objective.'}
[VALIDATOR] valid=True -> {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports …'}
[AGENT BRIDGE] Agent chose WAIT, nothing sent to Nav2. Reason: LiDAR path_blocked is False, but OpenCV visual evidence reports …
[AGENT BRIDGE] Nav2 goal finished: CANCELED
[AGENT RE-EVAL] OpenCV evidence has been clear again -- re-running the mission.
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0, 'n_components': 0, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.8, 'round_trip_ms': 760.0, 'timestamp': 1791588361.0007434, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=1.62m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.85m, recoveries=0
[VISION GUARD] obstruction at ~2.18 m is explained by LiDAR (nearest 2.02 m); not adding a stop.
[VISION GUARD] obstruction at ~1.75 m is explained by LiDAR (nearest 1.68 m); not adding a stop.
[NAV2 FEEDBACK] distance_remaining=0.25m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

**Nav2 server log (excerpt)**

```text
[bt_navigator]: Begin navigating from current location (-3.00, 0.00) to (0.00, 0.00)
[bt_navigator]: [navigate_to_pose] [ActionServer] Client requested to cancel the goal. Cancelling.
[controller_server]: Cancellation was successful. Stopping the robot.
[bt_navigator]: Begin navigating from current location (-2.03, 0.00) to (0.00, 0.00)
[controller_server]: Reached the goal!
[bt_navigator]: Goal succeeded
```

Note: `bt_navigator` also printed `Failed to get result for follow_path in node halt!` at each cancel
(B1 and B2). It was not investigated; the cancel was confirmed and the robot stopped.

---

## B3: OpenCV on

**Setup:** the spawn line and the Nav2 server log for this run were not captured, so the box
position and the stop clearance are not recorded.

**Result:** the guard stopped the mission, the agent chose WAIT, and the mission resumed after the
box was removed and finished SUCCEEDED.

| t (s) | Event |
|---|---|
| 0.00 | Nav2 accepted the goal |
| 10.97 | `VISION GUARD` hit 1 of 2, range 1.13 m |
| 11.90 | hit 2 of 2, range 1.04 m; cancel issued |
| 11.91 | Nav2 confirmed the cancel (4.4 ms after the decision) |
| 11.93 | goal finished CANCELED; agent had chosen WAIT |
| 31.66 | three clear results, mission re-run, NAVIGATE |
| 40.53 | goal finished SUCCEEDED |

**Bridge log (excerpt)**

```text
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0, 'n_components': 0, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.8, 'round_trip_ms': 813.0, 'timestamp': 1791588610.0809224, 'backend': 'url'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.67m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.60m, recoveries=0
[VISION GUARD] obstruction seen (1/2), range ~1.13 m
[VISION GUARD] obstruction seen (2/2), range ~1.04 m
[AGENT RE-EVAL] OpenCV reports an obstruction during an active goal -- cancelling the goal to re-evaluate the mission.
[AGENT RE-EVAL] Nav2 confirmed the goal was cancelled. Re-evaluating mission with current context.
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': True, 'corridor_occupancy': 0.1197, 'n_components': 1, 'largest_px': 4919, 'lateral_bin': 'center', 'est_range_m': 1.04, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.7, 'round_trip_ms': 926.0, 'timestamp': 1791588622.1574006, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports an obstruction in the forward corridor (range ~1.04 m, lateral=center, occupancy=0.1197); holding off on issuing a new navigation objective.'}
[VALIDATOR] valid=True -> {'action': 'WAIT', 'reason': 'LiDAR path_blocked is False, but OpenCV visual evidence reports …'}
[AGENT BRIDGE] Agent chose WAIT, nothing sent to Nav2. Reason: LiDAR path_blocked is False, but OpenCV visual evidence reports …
[AGENT BRIDGE] Nav2 goal finished: CANCELED
[AGENT RE-EVAL] OpenCV evidence has been clear again -- re-running the mission.
[AGENT BRIDGE] visual_evidence passed to agent: {'visual_obstruction': False, 'corridor_occupancy': 0.0, 'n_components': 0, 'source': 'opencv-5.0.0-aws-lambda', 'processing_ms': 7.6, 'round_trip_ms': 910.1, 'timestamp': 1791588641.9317017, 'backend': 'url'}
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=1.05m, recoveries=0
[VISION GUARD] obstruction at ~2.18 m is explained by LiDAR (nearest 2.11 m); not adding a stop.
[VISION GUARD] obstruction at ~1.91 m is explained by LiDAR (nearest 1.79 m); not adding a stop.
[NAV2 FEEDBACK] distance_remaining=0.30m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

---

## A1: OpenCV off

**Command**

```bash
ros2 run agric_orion agent_bridge_node --ros-args \
  -p mission:="Go to the field centre." -p use_visual_evidence:=false
```

**Setup:** box spawned when the robot was at world (-2.43, 0.00); box centre (-0.93, 0.00), near face -1.03.

**Result:** the agent chose NAVIGATE (no evidence supplied). The robot collided with the box and
stopped (observed in Gazebo). Nav2 nevertheless reported SUCCEEDED, 15.2 s after accepting the
goal. The `distance_remaining` values fall steadily to the goal, although the robot was stopped.

```text
[AGENT BRIDGE] Mission: "Go to the field centre."
[AGENT BRIDGE] visual_evidence passed to agent: None
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[VALIDATOR] valid=True -> {'action': 'NAVIGATE', 'x': 0.0, 'y': 0.0, 'reason': '…'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.60m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.87m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.07m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.35m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

---

## A2: OpenCV off

**Setup:** robot at world (-2.45, 0.00) when the box was spawned; box centre (-0.95, 0.00), near face -1.05.

**Result:** same as A1. The robot collided and did not move again. Nav2 reported SUCCEEDED, 15.3 s
after accepting the goal.

```text
[AGENT BRIDGE] visual_evidence passed to agent: None
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[VALIDATOR] valid=True -> {'action': 'NAVIGATE', 'x': 0.0, 'y': 0.0, 'reason': '…'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.62m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.90m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.10m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.37m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

---

## A3: OpenCV off, late spawn

**Setup:** the box was spawned deliberately late, when the robot was at world (-1.70, 0.00); box
centre (-0.20, 0.00), near face -0.30. Supplementary run: its geometry differs from the others.

**Result:** NAVIGATE, no stop, Nav2 SUCCEEDED 21.1 s after accepting the goal. The camera and LiDAR
messages in the log refer to the mapped `obstacle_1` ahead, not the box. LiDAR's nearest range of
1.88 m to `obstacle_1` (near face at x = 1.5) implies a true robot centre near x = -0.53, which is
consistent with a robot stopped against the box face at -0.30, while odometry placed it close to
the goal. That is an arithmetic cross-check, not a direct pose measurement.

```text
[AGENT BRIDGE] visual_evidence passed to agent: None
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.72m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.62m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.50m, recoveries=0
[VISION GUARD] obstruction at ~1.8 m is explained by LiDAR (nearest 1.88 m); not adding a stop.
[NAV2 FEEDBACK] distance_remaining=0.30m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

The `VISION GUARD ... explained by LiDAR` lines also appear in OpenCV-off runs. In those runs they
are log output only; the bridge ignores vision for the decision when the switch is off.

---

## V1: verification of the false success (OpenCV off)

**Purpose:** compare Gazebo's true robot pose with odometry after Nav2 reports SUCCEEDED.

**Setup:** box spawned when the robot was at world (-2.61, 0.00); box centre (-1.11, 0.00), near
face -1.21. The box was not removed.

**Bridge log (excerpt)**

```text
[AGENT BRIDGE] visual_evidence passed to agent: None
[MOCK AGENT] raw response: {'action': 'NAVIGATE', 'target': {'x': 0.0, 'y': 0.0}, 'reason': 'Field centre selected as requested. [vision context, source=mock]: …'}
[AGENT BRIDGE] Nav2 accepted the goal.
[NAV2 FEEDBACK] distance_remaining=2.62m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=1.87m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.67m, recoveries=0
[NAV2 FEEDBACK] distance_remaining=0.35m, recoveries=0
[AGENT BRIDGE] Nav2 goal finished: SUCCEEDED
```

**Position check, after SUCCEEDED**

```bash
gz topic -e -n 1 -t /world/agri_field/pose/info | grep -A8 'name: "agric_orion"' | head -12
```

```text
  name: "agric_orion"
  id: 50
  position {
    x: -1.4361999010092572
    y: 1.2766394735603953e-08
    z: 0.10000005216102309
  }
```

Odometry-based reading from the helper script (`clearance.py`, which adds the -3.0 start offset to
`/world_state`): `robot (-0.25, 0.00)`.

| Quantity | Value |
|---|---|
| Robot true x (Gazebo) | -1.436 m |
| Robot front (true x + 0.2) | -1.236 m |
| Box near face | -1.21 m |
| Gap, true | about 0.03 m (touching) |
| Robot x from odometry | -0.25 m |
| Distance from the goal at (0, 0), true | 1.44 m |
| Nav2 result | SUCCEEDED |

The robot was stopped against the box 1.44 m from the goal, while odometry placed it at the goal
and Nav2 reported success. One verification run.