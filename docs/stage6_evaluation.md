# Stage 6 Evaluation: OpenCV 5 visual evidence for Agri-ORION

Date: 2026-10-10. Platform: ROS 2 Jazzy, Gazebo Harmonic, OpenCV 5.0.0, AWS Lambda (eu-west-1).
Everything below was measured in simulation. Nothing was run on a real robot.

## 1. Claim

The robot's LiDAR is a single horizontal plane about 0.2 m above the ground. Nav2 and the
world-state node both use only that LiDAR. An object lower than the plane is invisible to the
whole stack, yet it can physically block the vehicle.

OpenCV 5 supplies one measurable visual cue for that blind spot. The cue changes a mission-level
decision (NAVIGATE to WAIT) and never commands motion. The deterministic validator and Nav2 are
unchanged.

**Not claimed:** real-world performance, robustness to natural imagery, or any statistical
significance. Counts are small and each is stated next to its result.

## 2. System under test

```text
Gazebo camera -> visual_evidence_node -> AWS Lambda (OpenCV 5 detector) -> JSON evidence
                                                                             |
LiDAR -> world_state ------------------------------------------------------>|
                                                                             v
                              agent_bridge_node -> mock agent -> validator -> Nav2 -> robot
```

Authority rule (enforced in code):

- LiDAR blocked or OpenCV obstruction means WAIT.
- OpenCV can never clear a LiDAR block and never authorises movement.
- OpenCV never publishes to `/cmd_vel`. `agent_contract.py` is unchanged.

Bridge parameters used: stop after 2 consecutive obstruction results, resume after 3 clear
results, evidence older than 1.5 s counts as unavailable (not as clear), and an obstruction within
0.6 m of LiDAR's nearest range is treated as already explained by LiDAR.

**Mocks, labelled honestly:** the agent is `MockNemotronAgent` (no LLM). The Stage 5 "vision
context" is still a mock (`source=mock`). Only `visual_evidence` is real OpenCV output, and its
`source` field names the OpenCV version and where it ran.

Detector (classical, no neural network): HSV saturation threshold (S > 60, V > 30), a corridor
region computed from camera geometry (ground distance 0.4 to 2.5 m, +/-0.25 m, camera height
0.15 m, focal length about 421 px), a 3x3 morphological opening, connected components with a
minimum area of 80 px, and range from the object's lowest image row, d = f*h/(v - cy).

## 3. Results

### 3.1 LiDAR blind spot (scripted sweep, 12 trials in shuffled order)

A red 0.2 x 0.4 m box at 1.2 m ahead; only the height varies. LiDAR column: does the forward
+/-10 degree sector show the box (reference without a box: 4.35 m)?

| Height | LiDAR sees it | Pixels changed vs empty-scene frame |
|---|---|---|
| 3 cm | no | 2,349 |
| 5 cm | no | 3,244 |
| 8 cm | no | 4,801 |
| 10 cm | no | 5,658 |
| 15 cm | no | 6,374 |
| 18 cm | no | 6,494 |
| 22 cm | yes (1.25 m) | 6,707 |
| 25 cm | yes | 6,860 |
| 30 cm | yes | 7,089 |
| 50 cm | yes | 8,545 |

The LiDAR threshold lies between 18 and 22 cm. The camera sees every height. The empty-scene
frame taken at the end of the sweep differed from the first by 0 pixels.

Physical blocking was observed for a static 0.15 m box (the robot could not push or cross it).
A 0.10 m box was not tested for blocking.

### 3.2 Detector on saved frames (OpenCV 5.0.0)

Sweep frames (thresholds were tuned on these, so this is not a held-out result): all 10 boxes
flagged, estimated range 1.19 to 1.21 m against a true distance of about 1.2 m, and 0 false
alarms on 3 clear frames.

Held-out scenarios (predictions written before running):

| Scenario | Truth | Detected | Range est. / true |
|---|---|---|---|
| clear (x2), side box, box beyond 2.5 m | no obstruction | correct (4 of 4) | n/a |
| green 0.10 m box | obstruction | yes | 1.19 / 1.20 m |
| box near corridor edge | obstruction | yes | 2.18 / 2.20 m |
| small 0.1 x 0.1 box | obstruction | yes | 1.44 / 1.45 m |
| **gray 0.10 m box** | obstruction | **missed** | - |
| **small box at 2.25 m** | obstruction | **missed** | - |

7 of 9 correct (4 of 4 negatives, 3 of 5 positives). The gray box is missed because the detector
keys on colour. The far small box is missed because only about 3 pixel rows of it fall inside the
corridor region. Both are documented design limits and were not tuned away.

### 3.3 Decision change on recorded data (22 scenes, replayed offline)

Same mock agent, same mission ("Go to the eastern field point"), with and without the evidence.

- NAVIGATE changed to WAIT in **13 of 22** scenes.
- **9** were objects LiDAR never saw: the six sweep boxes up to 18 cm and three 0.10 m held-out boxes.
- **4** were 22 to 50 cm boxes that LiDAR saw at 1.25 m, but `path_blocked` (threshold 1.0 m) was
  not yet true. Here vision gives earlier warning rather than unique information.
- The other 9 scenes stayed NAVIGATE: 7 true negatives (no false alarms) and the 2 known misses.

This is the decision function replayed on recorded sensor data, not a closed-loop run.

### 3.4 Cloud deployment

The same detector function runs as an AWS Lambda function (Python 3.12, x86_64, 1024 MB, 15 s
timeout, deployment zip about 74 MB, Function URL protected by a shared-secret header).

- Handler vs local detector on 22 saved frames: **22 of 22 identical**; 3 malformed requests
  returned 400 as designed.
- Real calls from the development machine (single location, single session): clear frame 200 and
  false; 0.10 m box frame 200, true, 1.19 m; wrong key 403; 20 repeated calls median 419 ms
  (worst 567 ms) in one test and median 497 ms (worst 659 ms) in another. The first call after
  idle took 1.0 to 2.4 s (new connection and possible cold start).
- Function time was about 8 to 20 ms per frame on warm calls; most of the round trip is network.
- In the closed loop the evidence arrives about 0.7 to 1.0 s after the frame it describes.
- If the call fails or times out, the node publishes nothing and the bridge treats the evidence
  as unavailable.

These are latency observations from one machine at one time, not general cloud benchmarks.

### 3.5 Closed-loop runs (goal: field centre at (0, 0); box appears about 1.5 m ahead mid-drive)

A scripted box (0.2 x 0.4 x 0.15 m, static) is spawned ahead of the robot while it is driving.

| Run | OpenCV | Guard ranges | Outcome | Stop clearance | Resumed after box removed | Nav2 result |
|---|---|---|---|---|---|---|
| B1 | on | 1.05, 0.90 m | WAIT, goal cancelled, stopped before the box | 0.59 m | yes | SUCCEEDED |
| B2 | on | 1.11, 0.89 m | same | 0.64 m | yes | SUCCEEDED |
| B3 | on | 1.13, 1.04 m | same | not recorded | yes | SUCCEEDED |
| A1 | off | none | NAVIGATE continued; robot collided and stopped | contact | n/a | SUCCEEDED (see 3.6) |
| A2 | off | none | same; robot never moved again | contact | n/a | SUCCEEDED (see 3.6) |
| A3 | off | none | box spawned late (robot at x = -1.70) | contact | n/a | SUCCEEDED (see 3.6) |

Clearance for B1 and B2 comes from Nav2's own "begin navigating from current location" pose at the
moment of resume, the 0.4 m body length from the URDF, and the box position printed by the spawn
script: gap = (box near face) - (robot x + 0.2). The clearance script that was run after each
trial is not valid, because it measured the robot's final position.

Timing from the logs (single runs):

- First sighting to cancel decision: 1.03 s (B1), 0.82 s (B2), 0.94 s (B3).
- Cancel decision to Nav2 confirming the cancel: 4.8 ms, 3.2 ms, 4.4 ms.
- No false stops in the three OpenCV-on runs.
- When approaching the mapped `obstacle_1`, the guard logged "explained by LiDAR" and added no
  stop.

Caveats: 3 runs per condition. The box was spawned at different robot positions (robot x at spawn:
B1 -1.51, B2 -2.59, A1 -2.43, A2 -2.45, A3 -1.70), so the geometry differed between runs. A3 was
spawned deliberately late and is supplementary. The raw terminal logs were not saved to files;
the decisive lines are quoted from the terminal.

### 3.6 Odometry false success (verification run, OpenCV off)

| | Value |
|---|---|
| Box centre / near face | x = -1.11 / x = -1.21 |
| Robot true x (Gazebo `pose/info`) | -1.436 (front at -1.236, gap about 0.03 m) |
| Robot x from odometry | -0.25 |
| True distance to the goal | 1.44 m |
| Nav2 result | SUCCEEDED |

Without OpenCV, the wheels kept turning against the box, odometry kept advancing, and Nav2
reported the mission complete while the robot was stuck. The OpenCV-off runs A1 to A3 are
consistent with this (A3: LiDAR's 1.88 m range to `obstacle_1` implies a true robot centre near
x = -0.53, against an odometry reading of about -0.24). This is one verification run.

### 3.7 Safety behaviours

- **Fail closed (optional switch, default off):** with `require_fresh_evidence` on and stale
  evidence, the bridge logged "evidence is required but missing or stale: WAIT" and nothing was
  sent to Nav2; with the switch off, the same stale evidence gave NAVIGATE (today's fallback).
  Tested on a clear scene.
- **LiDAR arbitration:** vision does not stop the robot for an obstruction LiDAR already explains
  (within 0.6 m), so mapped obstacles do not cause a permanent WAIT.
- **Resume:** after 3 consecutive clear results the bridge re-ran the mission and Nav2 completed
  the goal (3 of 3 OpenCV-on runs).

## 4. Limitations

- Simulation only: flat-coloured objects on a uniform grey ground, noise-free camera, no
  lighting variation. The colour-based method will not generalise to natural fields without
  further work.
- A gray (colourless) object was missed; a small object far away was missed.
- Detector thresholds were chosen on the sweep frames.
- 3 runs per condition; 1 odometry verification run; spawn positions varied between runs.
- B3 stop clearance was not recorded; raw logs were not saved to files.
- The LiDAR-explanation rule can mask a low object located within 0.6 m of a tall object ahead.
- Vision can only add caution. A false positive costs a delay (a WAIT), but there is no mechanism
  to clear a visual false positive that persists.
- Latency: the evidence is about 0.7 to 1.0 s old when it reaches the agent. At the robot's
  roughly 0.2 m/s that is about 0.2 m of travel before the decision. This is simulation speed.
- The camera sees only what is ahead of the robot's heading; the Nav2 path may curve.
- The stage 3 navigation limitation near `obstacle_1` (stalls on the way to (5, 0)) is
  unchanged and avoided by using the field-centre goal.
- Cloud numbers come from the Free plan, one region, one client location, sequential calls.

## 5. Reproduction (outline)

1. Python venv with `opencv-python-headless` 5.0.0; start the evidence node from that venv
   (`python -m agric_orion.visual_evidence_node`, parameters `backend`, `endpoint_url`, `timeout_s`).
2. `AGRI_KEY` is read from the environment; neither the key nor the URL belongs in the repository.
3. Scripts under `tools/`: `sweet_heights.py`, `scenarios.py`, `ab_decision_table.py`,
   `test_handler_local.py`, `local_function_url.py`, `call_url.py`, `spawn_box_ahead.py`.
4. Cloud code: `cloud/handler.py` plus `agric_orion/detect_obstruction.py`, packaged for Linux
   Python 3.12.
5. Bridge: `ros2 run agric_orion agent_bridge_node --ros-args -p mission:="Go to the field centre."
   -p use_visual_evidence:=true` (false for the baseline).

## 6. Open items

- [ ] Save the six run logs and screenshots under `stage6_data/runs/` and commit them.
- [ ] Record the demo video (one OpenCV-on and one OpenCV-off run).
- [ ] AWS evidence: Lambda configuration screenshot, CloudWatch invocation counts, architecture
      diagram, budget alert.
- [ ] README architecture section and a short explanation of the authority rule.
- [ ] Optional: more runs per condition with an identical spawn time.