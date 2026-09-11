# Agri-ORION

**Nebius × NVIDIA Global AI Hackathon 2026 — Physical AI track**

Agentic Physical AI for adaptive autonomous vehicle missions. A simulated
4-wheel skid-steer ground vehicle, built as an independent research
project, developed entirely from scratch and kept structurally separate
from the original ORION repository.

This README is a living document — edit it as the project evolves.

---

## 1. Project Concept

Long-term architecture:

```
Human mission
      ↓
AI mission reasoning        (NVIDIA Nemotron, via Nebius Token Factory)
      ↓
Mission planner
      ↓
ROS 2
      ↓
Navigation / control
      ↓
Autonomous vehicle
      ↓
Sensors / environment
      ↓
World state
      ↓
AI reasoning / replanning
```

**Core safety principle:** the AI reasoning layer must never directly
control motors. It operates at mission/decision level; deterministic
robotics (ROS 2, controllers, drive plugins) handles safety-critical
motion. Every stage of this project is built to preserve that boundary.

```
We want:      Sensors → Perception → World State → Future Agent
We reject:    Sensor → LLM → Motor
```

NVIDIA Cosmos Reason2 may later be investigated for physical-world
reasoning. Nothing LLM/agent-related has been implemented yet —
Stages 1 and 2 are pure deterministic robotics foundation.

---

## 2. Environment

- Ubuntu
- ROS 2 Jazzy
- Gazebo Harmonic (`gz sim`)
- Python (`ament_python` package)
- Standalone package: `agric_orion` — independent from the original
  ORION repository, may later move into an `agric_orion/` subfolder
  of it, but is not developed against it in any way.

---

## 3. Directory Structure (current)

```
workspace/ros2_ws/
    src/
        agric_orion/
            package.xml
            setup.py
            setup.cfg
            resource/agric_orion
            agric_orion/
                __init__.py
                world_state_node.py
            urdf/
                agric_orion.xacro
            worlds/
                agri_field.sdf
            config/
                bridge.yaml
            launch/
                display.launch.py
                gazebo.launch.py
                bridge.launch.py
                unified.launch.py
            docs/
                known_limitations.md
            test/
```

---

## 4. Vehicle Design

- **Type:** 4-wheel skid-steer, differential-drive style control
  (doubled per side — left pair matched, right pair matched).
- **Why not 2-wheel + caster:** more stable footprint, no caster
  friction fighting turns.
- **Why not Ackermann (true car steering):** would require steering
  joints, bicycle-model control math, and complicates future Nav2
  integration — disproportionate complexity for this project's actual
  goals, which center on mission-level reasoning, not steering realism.
- **Frames:** `base_footprint` (massless root, satisfies KDL's
  no-inertia-on-root constraint) → `base_link` (chassis) → 4 wheel
  links + `lidar_link` + `imu_link` + `camera_link`.

---

## 5. Stage 1 — Robotics Foundation (COMPLETE)

Established the deterministic robotics base the AI layer will sit on.

**Delivered:**
- ROS 2 workspace + `agric_orion` package (`ament_python`)
- URDF/xacro robot description, 4-wheel skid-steer
- Gazebo spawning (topic-based, via `robot_description`)
- `/cmd_vel` control via `gz::sim::systems::DiffDrive`
- `/odom` + `odom → base_footprint` TF
- `/joint_states` + wheel TF (`gz::sim::systems::JointStatePublisher`)
- Full bridge (`ros_gz_bridge`, YAML config) between `gz-transport` and
  ROS 2 for all of the above
- Unified launch file composing Gazebo + bridge

**Verified TF tree:**
```
odom → base_footprint → base_link → {front_left, front_right,
                                       rear_left, rear_right}_wheel
```

---

## 6. Stage 2 — Perception Layer (COMPLETE)

Added simulated sensors and a first, deliberately simple world-state
representation.

**Delivered:**
- Structured test world (`agri_field.sdf`): ground plane, boundary
  walls, one obstacle, three crop-row cylinders
- Simulated 2D LiDAR (`gpu_lidar`) → `/scan` (`LaserScan`)
- Simulated IMU → `/imu` (`Imu`)
- Simulated RGB camera → `/camera` (`Image`, 640×480, `rgb8`)
- Full sensor TF: `lidar_link`, `imu_link`, `camera_link`, all fixed
  children of `base_link`
- `world_state_node`: subscribes to `/odom` + `/scan`, publishes a
  JSON-encoded `std_msgs/String` on `/world_state` containing position,
  yaw, nearest forward obstacle distance, and a `path_blocked` flag

**Verified full TF tree:**
```
odom
 └── base_footprint
      └── base_link
           ├── front_left_wheel   (dynamic)
           ├── front_right_wheel  (dynamic)
           ├── rear_left_wheel    (dynamic)
           ├── rear_right_wheel   (dynamic)
           ├── lidar_link         (static)
           ├── imu_link           (static)
           └── camera_link        (static)
```

---

## 7. Key Design Decisions & Assumptions

- **World-state representation:** a plain Python `dict`, published as
  JSON inside `std_msgs/msg/String`, rather than a custom ROS 2 message
  type. Rationale: nothing downstream exists yet to require strict
  typing, and a custom message would need a separate `ament_cmake`
  interfaces package — disproportionate complexity for Stage 2. Revisit
  if/when a real consumer (e.g. a mission planner node) needs guarantees
  a loosely-typed JSON blob can't give.
- **Forward-obstacle detection:** uses a fixed ±10-sample sector around
  the LiDAR array's midpoint, assuming `angle_min = -π`/`angle_max = π`
  symmetry (so index 0 = directly behind, midpoint = straight ahead).
  This assumption breaks if the LiDAR's angular range is ever changed
  to something asymmetric.
- **`path_blocked` threshold:** a placeholder `1.0m` cutoff — not real
  obstacle-avoidance logic, just a simple signal for future consumers.
- **Sensor placement:** LiDAR forward-mounted (`0.15m` ahead of
  `base_link`), IMU centered, camera forward-facing — all attached via
  `fixed` joints, all collapsed into one physical body by Gazebo
  internally (see known limitations) but kept as separate TF frames via
  the original URDF.

---

## 8. Concepts Learned (cumulative)

**ROS 2 fundamentals:** workspace vs package, node/topic/publisher/
subscriber, launch files, ROS 2 CLI inspection tools, parameters.

**URDF / xacro:** link (visual/collision/inertial), joint types (fixed,
continuous), why `<inertial>` is mandatory, `xacro:property` /
`xacro:macro` for parameterized repeated structures, why a joint's
`<origin>` (not the link's own geometry) positions a child relative to
its parent.

**KDL root-link constraint:** `robot_state_publisher` forbids inertia on
the root link — fixed via a massless `base_footprint` root (also
standard convention for later Nav2 integration).

**TF:** `/tf` vs `/tf_static` (dynamic vs fixed joints), why a sensor
reading is meaningless without knowing its frame, how TF composes a
chain of transforms to convert a sensor-relative measurement into a
world/odom-relative one.

**gz-transport vs ROS 2 DDS:** two separate message systems;
`ros_gz_bridge` is an explicit translator, not automatic. Some type
pairs (e.g. `tf2_msgs/msg/TFMessage` ↔ `gz.msgs.Pose_V`) require a YAML
`config_file` bridge rather than the inline command-string syntax.

**Gazebo sensor plugins are not one-size-fits-all:** `gpu_lidar` and
`camera` are driven by the world-level `gz-sim-sensors-system` plugin;
IMU additionally requires its own dedicated `gz-sim-imu-system` model
plugin — declaring the sensor tag alone is not sufficient.

**Sensor physical limits are real, even in simulation:** a LiDAR's
`range_min` creates a genuine blind spot — a surface closer than that
threshold produces the same "no return" signal as something beyond
`range_max`. Discovered directly by testing, not assumed.

**Launch composition:** `IncludeLaunchDescription` composes existing,
independently-testable launch files rather than duplicating node
definitions — preserves the ability to debug one piece (spawn-only,
bridge-only) in isolation even after unifying.

---

## 9. Known Limitations

Full detail in `docs/known_limitations.md`. Summary:

1. **No `/cmd_vel` command timeout** (`gz::sim::systems::DiffDrive`) —
   a stale command persists indefinitely if the publisher stops.
   Accepted for now; planned mitigation is a supervisory watchdog node,
   not a redesign of the drive plugin.
2. **LiDAR min-range blind spot** causes `world_state_node` to report
   `path_blocked: false` at the exact moment an obstacle is closest
   (closer than `range_min`), because "too close" and "too far" both
   produce an identical `inf`/no-return signal. Accepted for Stage 2;
   real fix needs more context than a single `/scan` message provides.
3. **All simulated sensor covariances are zero** — Gazebo's default
   simulated sensors report as effectively noiseless. Real hardware
   never is; this will matter if/when any sensor-fusion or localization
   filter consumes this data later.
4. A stray `line_follower_robot` project (with its own `.git` and a
   `yolov8n.pt` file) exists at the `ros2_ws` **workspace root**, not
   inside `src/`. This previously broke `colcon`'s package discovery
   entirely (it collapsed the whole workspace into one misidentified
   package). Workaround in place (`~/.colcon/defaults.yaml` forcing
   `base-paths: [src]`); the stray content itself has not yet been
   moved or cleaned up.

---

## 10. Recurring Bug Patterns (worth remembering)

Real mistakes made and fixed during development — kept here because the
patterns recur and are faster to recognize than to re-diagnose:

- Missing `=` in an XML attribute (`type"gpu_lidar"` instead of
  `type="gpu_lidar"`) — silent-looking but fatal XML parse error.
- URDF elements (`<link>`, `<joint>`) accidentally nested inside a
  `<gazebo>` block instead of being top-level `<robot>` children.
- A joint's `<child link="...">` not matching the actual `<link
  name="...">` string exactly (e.g. `camera_link` vs `camera-link`) —
  URDF does exact string matching, no fuzzy correction.
- C++ namespace typos in Gazebo plugin `name=` attributes — single
  colon instead of double (`systems:Imu` vs `systems::Imu`), or wrong
  capitalization (`Systems` vs `systems`) — Gazebo's error log lists the
  actual detected plugin name/aliases, which is the fastest way to spot
  the mismatch.
- YAML key typos in `bridge.yaml` (e.g. `ros_topic_nam`) — silently
  produces a malformed bridge entry rather than an obvious parse error.
- Duplicate/leftover XML tags (e.g. two `<odom_publish_frequency>` tags)
  from incremental edits not being cleaned up.
- Stale RViz topic subscriptions showing `Status: OK` with zero
  messages received — always check the actual message/point *count*,
  not just the status icon.
- `colcon` silently misidentifying the whole workspace as a single
  package when a stray `package.xml` exists at the workspace root
  above `src/` — always check `colcon list` output path, not just that
  a build "succeeded."

---

## 11. How to Run

```bash
cd ~/workspace/ros2_ws
colcon build --packages-select agric_orion
source install/setup.bash
ros2 launch agric_orion unified.launch.py
```

In a separate terminal, once running:

```bash
ros2 run agric_orion world_state_node
ros2 topic echo /world_state
```

Drive the robot manually:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}" --rate 10 -t 5
```

(`-t 5` limits the publish to 5 seconds — see Known Limitation #1 on
why an unbounded `cmd_vel` stream is best avoided during manual testing.)

---

## 12. Progress Checklist

- [x] Stage 1 — ROS 2 + Gazebo robotics foundation
- [x] Stage 2 — Perception layer (LiDAR, IMU, camera, world state)
- [ ] Stage 3 — TBD (navigation / `ros2_control` / first Nemotron
      integration — not yet scoped)

---

## 13. Notes for Future Self / Judges

This project is deliberately built incrementally, with every milestone
independently tested before moving on, and every real bug documented
rather than silently patched. The goal has been to understand the full
system well enough to explain it, not just to produce a working demo —
several genuine limitations (drive timeout, LiDAR blind spot) are known,
understood, and consciously deferred rather than accidental gaps.