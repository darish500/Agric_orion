# Agri-ORION

**An OpenCV 5 visual safety cue for an agentic field robot.** A simulated 4-wheel ground vehicle
(ROS 2 Jazzy, Gazebo Harmonic) whose LiDAR cannot see low objects, plus a camera pipeline that can.
OpenCV 5 runs on AWS Lambda, turns each camera frame into a small JSON measurement, and that
measurement changes the robot's next decision. The AI layer never touches `/cmd_vel`.

Built for the **OpenCV AI Competition 2026 (powered by AWS)**. Stages 1 to 5 were built earlier for the
Nebius x NVIDIA Global AI Hackathon and are the foundation.

| | |
|---|---|
| **Status (2026-10-13)** | Stages 1 to 6 work in simulation. Remaining: demo video, AWS evidence, final submission. |
| **Evidence** | `docs/stage6_evaluation.md` (results), `docs/stage6_run_logs.md` (every live run), `docs/Agri-ORION_Technical_Report.pdf` |
| **Scope** | Simulation only. Nothing was run on a real robot. |
| **License** | To be added before submission (`LICENSE` file and `package.xml`). |

---

## 1. The pitch in 40 seconds

The same scene, the same mission ("Go to the field centre"), a 0.15 m box appearing in front of the
robot while it drives. Only one switch differs.

| Without OpenCV evidence | With OpenCV evidence |
|---|---|
| LiDAR sees nothing (the box is below its scan plane). The robot drives into the box and stops. | The camera sees the box. The system cancels the goal and the robot stops about 0.6 m before it. |
| **Nav2 reports SUCCEEDED**, because wheel odometry kept counting while the wheels spun. The true position was 1.44 m from the goal. | When the box is removed, the system resumes by itself and finishes. |
| 3 live runs, plus 1 run that read Gazebo's true pose | 3 live runs |

Three runs per condition is a clear demonstration, not a statistical result. Details and every
caveat are in the evaluation document.

---

## 2. Terms for a first-time reader

| Term | Meaning here |
|---|---|
| **NAVIGATE / WAIT** | The two decisions the mission agent can make: send a goal to Nav2, or send nothing. |
| **Mission agent** | The component that turns a mission text into a structured objective. Today it is a deterministic stand-in (see `MockNemotronAgent`). |
| **`MockNemotronAgent`** | A scripted agent with the interface of a language-model agent. It is named after NVIDIA Nemotron, the model the project was first built to call through Nebius. Live access was blocked by a billing-country restriction, so a mock (including a simulated API failure) keeps the architecture testable. **No LLM is called.** |
| **Stage 5 vision context** | A mock "vision agent" from Stage 5 that returns a fixed text description of the scene (`source=mock`). It is not perception, and it is separate from the real OpenCV evidence of Stage 6. |
| **Visual evidence** | The JSON the OpenCV detector produces: obstruction flag, range, lateral bin, occupancy. Real perception, labelled with its source. |
| **Contract validator** | `agent_contract.py`. Checks every agent proposal: trusted place names, map bounds, allowed actions. |
| **LiDAR scan plane** | The 2D LiDAR sees one horizontal slice about 0.2 m above the ground. Lower objects are invisible to it. |
| **`path_blocked`** | A LiDAR flag, true when the nearest obstacle ahead is closer than 1.0 m. |
| **Odometry** | The robot's position estimated from wheel rotation. It drifts when wheels slip. |
| **Nav2** | The standard ROS 2 navigation stack (NavFn planner, Regulated Pure Pursuit controller). |

---

## 3. Architecture

```text
Human mission
     |
     v
Mission agent (mock, swappable)  <---- visual evidence (OpenCV 5) + LiDAR world state
     |
     v
Contract validator (agent_contract.py)
     |
     v
Nav2  ->  /cmd_vel  ->  vehicle

Camera -> visual_evidence_node -> AWS Lambda (OpenCV 5 detector) -> /visual_evidence (JSON)
```

**Authority rule, enforced in code:**

- LiDAR blocked, or OpenCV obstructed: the agent chooses WAIT.
- OpenCV can never clear a LiDAR block and never authorises movement.
- Neither OpenCV nor the agent publishes to `/cmd_vel`.
- Missing or stale evidence (older than 1.5 s) counts as **unavailable, never as clear**. An optional
  `require_fresh_evidence` switch turns that into WAIT (fail closed).
- If LiDAR already explains an obstruction (within 0.6 m of the visual range), vision adds no extra
  stop, so mapped obstacles do not cause a permanent WAIT.

---

## 4. Why OpenCV 5, honestly

The detector uses standard operations that also exist in OpenCV 4: HSV conversion, thresholding,
morphological opening, connected components. **We do not claim an algorithm that only OpenCV 5 can run.**
What we can state:

- The system is built, pinned and tested on OpenCV 5.0.0.
- The Lambda function runs OpenCV 5.0.0. Every evidence message says so in its `source` field
  (`opencv-5.0.0-aws-lambda`), and the evidence node reports an error if it is started with another version.
- The ten sweep frames give **identical output under OpenCV 4.13.0 and 5.0.0** (range and occupancy), so
  the pipeline is portable across both versions.

> TODO before submission: read the competition's judging criteria for what substantive OpenCV 5 use is
> expected to mean, and add an honest OpenCV-5-specific angle if one is found.

---

## 5. Stages

| Stage | Theme | Status | Main artifacts |
|---|---|---|---|
| 1 | Robotics foundation | complete | xacro robot, `DiffDrive`, `/cmd_vel`, `/odom`, TF, `ros_gz_bridge` config, `unified.launch.py` |
| 2 | Perception layer | complete | `gpu_lidar` `/scan`, IMU `/imu`, RGB camera `/camera` (640x480 `rgb8`), `world_state_node` (`/world_state`) |
| 3 | Deterministic navigation | complete | prebuilt map (`generate_map.py`), static `map -> odom`, Nav2, `nav2_eval_node`, `test_follow_path` |
| 4 | Agentic mission reasoning | complete (mock agent) | `agent_contract.py`, `MockNemotronAgent`, `agent_bridge_node` (`NavigateToPose`), sustained-blockage re-evaluation |
| 5 | Physical-world context | complete | `mission_context_node`, `MockVisionAgent` / `vision_context_node` (mock), evaluation notes |
| 6 | OpenCV 5 visual evidence | complete in simulation | blind-spot measurement, detector, AWS Lambda, authority rule, vision guard, evaluation |

### Stage 6 results

| Experiment | Result |
|---|---|
| LiDAR blind spot (height sweep, 3 to 50 cm) | LiDAR missed every box up to 18 cm and saw boxes from 22 cm. The camera saw all heights. |
| Detector on the sweep frames (thresholds were tuned on these) | 10 of 10 boxes flagged, 3 of 3 empty frames clear, range error 0.01 m |
| Detector on 9 held-out scenarios | 7 of 9 correct: 4 of 4 negatives, 3 of 5 positives. Misses: a gray box and a small box far away. |
| Decision replay on 22 recorded scenes | NAVIGATE became WAIT in 13 (9 for objects LiDAR never saw). The 7 true negatives are the 4 held-out negatives above plus 3 empty-scene frames from the sweep set. |
| Closed loop, evidence on | 3 of 3 stopped before the box (clearance 0.59 m and 0.64 m recorded for 2 runs), resumed, finished |
| Closed loop, evidence off | 3 of 3 hit the box; Nav2 reported SUCCEEDED each time |
| True pose check (evidence off) | Robot touching the box 1.44 m from the goal; odometry said it was at the goal |
| Cloud | Lambda round trip about 0.4 to 0.5 s from the dev machine, 0.7 to 1.0 s inside the closed loop |

---

## 6. What is real and what is mocked

| Component | Real or mock |
|---|---|
| Robot, sensors, Nav2, TF | real software, simulated physics |
| OpenCV 5 evidence (`/visual_evidence`) | **real**; `source` names the version and where it ran |
| Mission agent | **mock** (`MockNemotronAgent`). No LLM is called. |
| Stage 5 vision context (`/vision_context`) | **mock** (`source=mock`) |
| AWS Lambda detector | real, deployed in `eu-west-1` |

---

## 7. Environment and build

- Ubuntu, ROS 2 Jazzy, Gazebo Harmonic, Nav2; Python 3.12
- OpenCV 5.0.0 (`opencv-python-headless`) in a separate virtual environment
- Optional: an AWS account. Everything also runs with the local detector.

```bash
cd ~/workspace/ros2_ws
colcon build --packages-select agric_orion
source install/setup.bash
```

Rebuild after every edit to files inside `agric_orion/agric_orion/`. ROS nodes run the *installed* copy,
and an old build silently runs old code.

### OpenCV 5 virtual environment

```bash
python3 -m venv --system-site-packages ~/workspace/ros2_ws/venv_cv5
source ~/workspace/ros2_ws/venv_cv5/bin/activate
pip install opencv-python-headless
python -c "import cv2; print(cv2.__version__)"      # must print 5.x
```

`ros2 run` uses the **system** Python (OpenCV 4.x). Start the evidence node from the venv with
`python -m agric_orion.visual_evidence_node`. The venv installs numpy 2.x, so keep it out of terminals
that run other ROS nodes.

### Pinned dependencies

Generate and commit the exact versions you ran:

```bash
source ~/workspace/ros2_ws/venv_cv5/bin/activate
pip freeze | grep -i -E "^(opencv|numpy|pillow)" > requirements.txt
```

---

## 8. Running it

Use one terminal per item. In each, first run
`source /opt/ros/jazzy/setup.bash && source ~/workspace/ros2_ws/install/setup.bash`.

```bash
ros2 launch agric_orion unified.launch.py          # 1  Gazebo, bridge, map server
ros2 launch agric_orion navigation.launch.py       # 2  Nav2
ros2 run agric_orion world_state_node              # 3  LiDAR + odometry -> /world_state
ros2 run agric_orion vision_context_node           # 4  mock vision context (the bridge waits for it)
```

**5. Evidence node** (venv active). Local detector, no AWS:

```bash
python -m agric_orion.visual_evidence_node --ros-args -p backend:=local
```

Or through AWS Lambda (keep the key and URL out of the repository):

```bash
export AGRI_KEY="..."        # shared secret, also set as API_KEY on the Lambda function
python -m agric_orion.visual_evidence_node --ros-args \
  -p backend:=url -p endpoint_url:="$AGRI_URL" -p timeout_s:=6.0
```

**6. The bridge (starts the mission):**

```bash
ros2 run agric_orion agent_bridge_node --ros-args \
  -p mission:="Go to the field centre." -p use_visual_evidence:=true
```

Use `use_visual_evidence:=false` for the baseline without OpenCV.

### Bridge parameters

| Parameter | Default | Meaning |
|---|---|---|
| `mission` | `Go to the norther inspection point.` | Mission text sent to the agent |
| `use_visual_evidence` | `true` | Pass OpenCV evidence to the agent and run the vision guard |
| `evidence_max_age_s` | `1.5` | Older evidence counts as unavailable, not clear |
| `require_fresh_evidence` | `false` | If true and evidence is unavailable: WAIT (fail closed) |
| `vision_stop_hits` | `2` | Consecutive obstruction results that cancel an active goal |
| `vision_resume_hits` | `3` | Consecutive clear results that re-run the mission |
| `lidar_explain_tol_m` | `0.6` | Visual obstruction within this of LiDAR's nearest range is "explained by LiDAR" |

### Mission texts the mock agent understands

| Mission | Outcome |
|---|---|
| `Go to the field centre.` | NAVIGATE to raw coordinates (0, 0); used for the Stage 6 runs |
| `Go to the eastern field point.` | NAVIGATE to (5, 0). **Nav2 stalls beside `obstacle_1` on this route.** |
| `Go to the northern inspection point.` | NAVIGATE to (-3, 3) |
| `Inspect the southern section.` | rejected by the validator (location not in the trusted table) |
| `Move to the eastern side of the field.` | rejected by the validator (target outside the map bounds) |
| `What is the weather today?` | not a navigation mission |

The trusted places are `northern_inspection_point`, `home_base` and `eastern_field_point`. Raw coordinates
are accepted only inside the +/-6 m map bounds.

---

## 9. Reproducing the experiments

Scenarios are scripted with `gz service`; nothing is dragged in the GUI.

| Script | What it does |
|---|---|
| `capture_trial.py <name>` | saves one `/camera` frame (PNG) and a LiDAR summary (JSON) |
| `sweet_heights.py` | height sweep: LiDAR vs camera (the blind-spot table) |
| `scenarios.py` | held-out detector scenarios |
| `ab_decision_table.py` | replays recorded scenes through the agent with and without evidence |
| `test_handler_local.py` | checks the Lambda handler against the local detector (22 frames, 3 bad requests) |
| `local_function_url.py` | local stand-in for a Lambda Function URL |
| `call_url.py` | calls the real Function URL (reads `AGRI_URL`, `AGRI_KEY` from the environment) |
| `spawn_box_ahead.py [dist] [name]` | spawns a 0.15 m box ahead of the robot's heading |
| `clearance.py <box_x> <box_y>` | odometry-based gap to a box. **Not a true position.** |

Closed-loop run: start everything in section 8, wait about 6 s after `Nav2 accepted the goal`, then:

```bash
python3 tools/spawn_box_ahead.py 1.5
gz service -s /world/agri_field/remove --reqtype gz.msgs.Entity \
  --reptype gz.msgs.Boolean --timeout 2000 --req 'name: "late_box" type: MODEL'   # when stopped
```

True robot position from Gazebo (odometry can disagree when wheels slip):

```bash
gz topic -e -n 1 -t /world/agri_field/pose/info | grep -A8 'name: "agric_orion"' | head -12
```

---

## 10. AWS deployment and security

```bash
cd ~/workspace/ros2_ws/src/agric_orion
rm -rf build_lambda && mkdir -p build_lambda/pkg
pip install --target build_lambda/pkg \
  --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 \
  --implementation cp --python-version 3.12 --only-binary=:all: \
  opencv-python-headless numpy
cp cloud/handler.py agric_orion/detect_obstruction.py build_lambda/pkg/
cd build_lambda/pkg && zip -r -q ../lambda_opencv5.zip . && cd ../..
```

Upload the zip to a private S3 bucket and create a Python 3.12 / x86_64 Lambda function from it (handler
`handler.handler`, 1024 MB, 15 s timeout). Add the environment variable `API_KEY` and a Function URL.

The Function URL has **no AWS-level authentication**; the function itself requires a shared secret in the
`x-api-key` header (wrong key returns 403). Before judges use it:

- [ ] Rotate the key, and do not put it in the repository, the video or the report.
- [ ] Set a reserved-concurrency limit on the function.
- [ ] Set a budget alert (the account is on the Free plan, which stops at its credit limit).
- [ ] Share the new key privately in the submission notes, or offer a live screen-share instead.
- [ ] Delete the function, URL and bucket after judging.

Images are processed in memory and not stored.

---

## 11. Repository layout

```text
agric_orion/                      (repository root, ROS 2 package)
    package.xml  setup.py  setup.cfg  requirements.txt  resource/
    agric_orion/                  Python package (installed by colcon)
        world_state_node.py       /scan + /odom -> /world_state
        agent_contract.py         deterministic validator
        mission_agent.py          MockNemotronAgent
        agent_bridge_node.py      agent -> validator -> NavigateToPose, vision guard
        mission_context_node.py   Stage 5 temporal / identity context
        vision_agent.py  vision_context_node.py   Stage 5 mock vision
        detect_obstruction.py     Stage 6 OpenCV 5 detector (pure function)
        visual_evidence_node.py   Stage 6 /camera -> /visual_evidence (local or URL)
        nav2_eval_node.py  test_follow_path.py  generate_map.py
    cloud/handler.py              Stage 6 Lambda handler
    tools/                        experiment scripts (section 9)
    launch/  config/  maps/  urdf/  worlds/  test/
    docs/                         stage reports, figures, known_limitations.md
```

World file `worlds/agric_field.sdf` has the internal world name `agri_field` (used in `gz service` paths).
Robot model name: `agric_orion`.

---

## 12. Known limitations

1. **Simulation only.** Flat-coloured objects on uniform grey ground, a noise-free camera, no lighting
   variation. The colour test will not transfer to natural fields without more work.
2. **Detector misses** gray (colourless) objects and small objects far away. Thresholds were tuned on the
   sweep frames.
3. **Odometry false success.** A robot stuck against an obstacle keeps "moving" on wheel odometry and Nav2
   reports SUCCEEDED. Without a visual cue the system cannot tell. Not fixed.
4. **Small samples.** Three live runs per condition; the box was spawned at different robot positions; the
   stop clearance of one run (B3) was not recorded.
5. **Blocking was observed for a 0.15 m static box only.**
6. **The camera looks along the robot's heading,** while the planned path may curve.
7. **Evidence latency** about 0.7 to 1.0 s (mostly network), roughly 0.2 m of travel at 0.2 m/s.
8. **LiDAR arbitration can mask** a low object lying within 0.6 m of a tall object ahead.
9. **Nav2 stalls beside `obstacle_1`** on the route to (5, 0) (seen in two runs); Stage 6 avoids it.
10. **Earlier-stage limits:** `DiffDrive` has no command timeout, simulated sensors are noiseless, and
    `map -> odom` is a static transform. See `docs/known_limitations.md`.

---

## 13. Design decisions and lessons

- **JSON in `std_msgs/String`** for `/world_state`, `/vision_context` and `/visual_evidence`, not custom
  messages: nothing downstream needed strict typing.
- **Classical OpenCV before any neural network:** sufficient in the controlled simulation, and its failures
  are explainable.
- **Perception outputs measurements, not reasoning.** Deciding what they mean belongs to the agent.
- **Asymmetric authority:** vision can add caution, never remove it.
- **Honest labelling:** every evidence message carries its `source`; mock components say `mock`.
- **Timebox external services and keep them swappable.** When live model access was blocked, the mock kept
  the architecture testable.
- **Check what a node actually imports.** `ros2 run` used OpenCV 4.13 while the venv had 5.0.0.
- **Odometry is not ground truth.** Compare with Gazebo's pose before trusting "SUCCEEDED".
- **Script every experimental condition.** GUI dragging is not reproducible.

---

## 14. Roadmap

- [x] Stages 1 to 6
- [ ] Demo video, led by the 40-second comparison in section 1
- [ ] AWS evidence: Lambda configuration, CloudWatch invocation counts, budget alert
- [ ] A second cue for gray objects (compare the corridor with the expected ground appearance, or use
      edges and texture)
- [ ] A real language-model agent behind the existing interface (timeboxed)
- [ ] An honest OpenCV-5-specific angle, if one exists (section 4)
- [ ] More runs per condition with an identical spawn time
- [ ] Later: active (viewpoint-changing) perception, scene-change detection, AMCL localization

---

## 15. Documentation index

| File | Contents |
|---|---|
| `docs/Agri-ORION_Technical_Report.pdf` | Competition technical report |
| `docs/stage6_evaluation.md` | Stage 6 claim, results, limitations, reproduction |
| `docs/stage6_run_logs.md` | Formatted excerpts of every live run, with timelines |
| `docs/figures/` | Architecture and agent-loop diagrams, result figures |
| `docs/stage5_*.md`, `stage4_summary.md` | Earlier stage design and evaluation notes |
| `docs/known_limitations.md` | Early-stage limitations in detail |