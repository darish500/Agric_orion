# Stage 5 — Vision Experiment (Milestone 5.4)

This document records the Milestone 5.4 investigation into whether
visual physical reasoning provides a capability genuinely missing from
the existing symbolic `/world_state` + `/mission_context` pipeline,
before any commitment to a specific vision model or its integration
into the live system.

## Method

Five controlled scenarios were captured directly from the robot's real
onboard `/camera` topic (viewed via `rqt_image_view`, not Gazebo's
external orbit-view camera, which was ruled out early as it shows the
robot's own body from a third-person angle the robot itself never
sees). Each frame was submitted to several vision-language models via
Roboflow's Open Prompt playground (GPT-6 Astra, Claude Opus 5.5,
Gemini 3.5 Flash, Qwen3.8 Max), with the same prompt: "Describe what's
in front of this vehicle and whether its path looks blocked."

This is a manual, no-code test, deliberately run before writing any
integration code, per the project's own "prove it before building it"
principle.

## Results by scenario

### 1. Obstacle directly ahead (two boxes)
All four models correctly identified two obstacles and specifically
flagged that the gap between them was too narrow to pass through.
**New capability**: `nearest_obstacle_m` gives a single distance; it
has no concept of "two objects with an unsafe gap between them."

### 2. Crop-row scene (two cylinders, no boxes)
All four models correctly called the cylinders "posts" or "pillars,"
never "obstacles" -- independently reproducing the same
obstacle/crop-row distinction already hardcoded in
`mission_context_node.py`'s KNOWN_OBJECT registry, but without needing
a pre-built registry at all.
**Limitation**: 2 of 4 models incorrectly flagged the path as
"blocked" because of the field's distant boundary wall, which is not
an actual near-term obstruction.

### 3. Open field (nothing nearby)
This should be the easiest possible case.
**Limitation**: 2 of 4 models still said "blocked," again reading the
far boundary wall as an immediate obstruction. The other 2 correctly
read it as open, but noted the image was too low-detail to be fully
confident.

### 4. Partially obstructed (obstacle off-center)
All four models correctly identified the obstacle's position (left of
center) and explicitly identified a clear, open lane to its right.
**New capability**: no existing symbolic field expresses "clear to the
left" vs "clear to the right" -- the forward-sector LiDAR check has no
notion of lateral clearance at all.

### 5. Changed scene (object newly appeared)
Roboflow's Open Prompt tool does not support submitting two images in
a single message, so a true side-by-side "what changed" test could not
be run. As a fallback, the same frame was described twice
independently (before and after a yellow box entered frame), and the
two text outputs were compared by hand.
**Result**: the appearance of the new object was clearly and
prominently described in the "after" text ("a tall yellow rectangular
block dominates the left foreground, casting a dark shadow").
**Confound**: the "after" description also picked up a second red
block not mentioned in the "before" description, most likely because
the robot's own viewpoint shifted slightly between the two captures,
not because a second object actually appeared. This is a real limit of
the *diffing two independent descriptions* approach specifically, not
necessarily of a model directly comparing two images at once (which
could not be tested here).

## Conclusion

Vision reasoning adds two capabilities the current symbolic pipeline
genuinely lacks:
- **Object identity/relationship** -- distinguishing crop rows from
  obstacles without a hardcoded registry, and describing gaps between
  multiple objects.
- **Lateral spatial awareness** -- clear-left/clear-right judgments the
  forward-sector LiDAR check cannot make.

Vision reasoning is **not a reliable replacement** for LiDAR's
distance grounding: multiple models, across multiple scenarios,
misjudged near vs. far without an actual distance measurement,
incorrectly calling a distant wall an immediate blockage.

**Decision**: this motivates a hybrid direction for later milestones
(5.6/5.7) -- vision as a *supplement* to the existing
`/mission_context` pipeline for identity/relationship/lateral
questions, never as a *replacement* for LiDAR's precise, grounded
distance measurement. Milestone 5.5 should evaluate the best
available vision model for this supplementary role, since NVIDIA
Cosmos Reason2 is not currently accessible (same access-tier
limitation category as Nemotron in Stage 4) -- Cosmos itself remains
worth revisiting if/when access becomes available, but is not blocking
this conclusion.