## Spin recovery behavior fails with "Costmap is not available" (Stage 3)

When bt_navigator's default recovery escalates to the Spin behavior,
nav2_behaviors sometimes reports "Costmap is not available" and aborts
the spin immediately, apparently due to a timing gap right after the
local costmap is cleared/reset (observed directly following a
"Received request to clear entirely the local_costmap" event).

This is a known-category Nav2 timing issue in the behavior server's
internal costmap client, not a misconfiguration in our YAML -- topic
names (local_costmap_topic, global_costmap_topic) were verified correct
against the actual published topics.

Decision: accepted for Stage 3 baseline. Mitigated indirectly by
increasing inflation_radius (0.55 -> 0.75) so recovery is triggered
less often in the first place. Revisit only if recovery behaviors
become load-bearing for a later milestone.

## Tight-corner navigation near obstacle barrier fails to clear (Stage 3)

Sending a goal that requires the robot to turn around obstacle_1's
corner shortly after spawn (~x=1.0, close to the obstacle's face at
x=1.5) reliably triggers RegulatedPurePursuitController's collision
check, aborting repeatedly. BT Navigator's replanning loop and Spin
recovery both engage as designed, but neither resolves it -- Spin
additionally fails with an unrelated "Costmap is not available" error
(see above).

Diagnosed precisely via /odom position logging at the failure point:
the robot is executing a ~27 degree turn only ~0.5m from the obstacle
face, well within a tight corner rather than open space.

Attempted fixes: increasing inflation_radius (0.55 -> 0.75 -> 0.65) and
reducing controller lookahead_dist (0.6 -> 0.4). Neither fully resolved
it -- likely because the actual constraint is geometric (turn radius
required vs. available clearance at that specific corner, this early
in the route), not a simple cost-gradient or lookahead tuning problem.

Decision: accepted for Stage 3 baseline. Milestone 3.5 (first
autonomous goal) validated instead using a goal that does not require
this maneuver, confirming the full map -> plan -> control -> arrive
pipeline works correctly end to end. This tight-corner case is reserved
as the explicit test for Milestone 3.6 (obstacle handling), where it
provides a real, already-diagnosed starting point rather than a fresh
unknown.

Possible future directions (not attempted yet): widening the gap
between spawn and obstacle_1's corner, reducing robot_radius to better
match the vehicle's actual (non-circular) footprint, or trying an
alternate controller plugin (e.g. DWB) with different turning behavior
near costed regions.


## Tight-corner navigation near obstacle barrier fails to clear (Stage 3, extensively diagnosed)

Any autonomous goal requiring the robot to route around obstacle_1's
corner near spawn (~x=1.0-1.5) reliably triggers
RegulatedPurePursuitController's collision check and aborts, regardless
of how far away the ultimate goal is (confirmed with goals directly
behind the barrier, north of it, and well south of it at y=-3.5 -- all
routed close to the same corner and failed identically).

Root cause, as best diagnosed: NavfnPlanner (Dijkstra-based) minimizes
distance + costmap penalty, and with the cost gradients tested, cutting
the corner close is cheaper than a wide detour -- so the global plan
itself produces a tight-radius turn at that corner. The controller then
cannot execute that turn without projecting into the inflated zone,
regardless of speed/lookahead tuning.

Fixes attempted, in order, each based on a distinct correct hypothesis:
1. inflation_radius: 0.55 -> 0.75 -> 0.65 (planner + controller
   costmaps) -- widens/narrows the cost zone; did not change the
   outcome.
2. lookahead_dist: 0.6 -> 0.4 (tighter following, intended to reduce
   projected-arc overshoot) -- no change.
3. cost_scaling_factor: 3.0 -> 8.0 (steeper cost gradient, intended to
   make the planner prefer a wider detour) -- no change observed before
   time was reallocated.
4. Curvature- and cost-based velocity regulation
   (use_regulated_linear_velocity_scaling,
   use_cost_regulated_linear_velocity_scaling,
   regulated_linear_scaling_min_radius: 0.9) -- intended to slow the
   robot for the sharp turn; did not resolve it either.

Secondary, independent bug also present throughout: the Spin recovery
behavior fails with "Costmap is not available" immediately after a
local costmap clear event -- a likely Nav2 timing issue in the
behavior server's internal costmap client, not a config error (topic
names verified correct).

Decision: accepted as a known Stage 3 limitation. Not resolved through
config tuning alone -- likely needs either a different controller
plugin (e.g. DWB, which samples candidate trajectories rather than
tracking a fixed lookahead point, or MPPI), a smaller/more accurate
robot footprint than the current circular robot_radius approximation,
or restructuring the environment (more clearance between spawn and the
obstacle's corner).

Milestone 3.5 (first autonomous goal) was validated instead using goal
(-3, 3), which does not require this maneuver -- confirmed the full
map -> plan -> control -> arrive pipeline works correctly end to end.
This corner case is reserved as a documented open problem, not a
blocker for Stage 3's remaining milestones.

## Goal-arrival overshoot causes unintended obstacle approach (Stage 3, final diagnosis)

Across multiple evaluation attempts (Milestone 3.7), goals at varying
distances and directions from spawn consistently ended with the robot
driving into/toward obstacle_1's barrier, regardless of the goal's
actual direction -- including a goal requiring only a ~3m straight-line
drive with negligible turning (0, 0.3), which ruled out the earlier
sharp-turn-at-start hypothesis.

Final diagnosis: the robot appears to overshoot short-distance goals
rather than decelerating and registering arrival cleanly via
SimpleGoalChecker's tolerance -- continuing in its prior heading past
the intended stopping point. In this environment's layout, continuing
past nearly any goal eventually leads toward obstacle_1, which is why
the failure consistently manifests as "drove into the barrier"
regardless of the goal actually specified.

Diagnostic history (each hypothesis tested with real evidence, in
order): inflation_radius tuning, controller lookahead_dist tuning,
cost_scaling_factor, curvature/cost-based velocity regulation, and
finally a controlled near-straight-line test that isolated the true
mechanism to goal-arrival behavior rather than turning or obstacle
proximity.

Decision: accepted as a Stage 3 baseline limitation, not resolved
within Stage 3's timeline. Milestone 3.5's validated success case
(-3, 3) and Milestone 3.6's dynamic-obstacle case remain valid,
confirmed results -- both completed before this overshoot pattern was
fully isolated, and neither required the robot to travel a very short
distance to a nearby goal, which may be why they succeeded while the
Milestone 3.7 evaluation goals (several of which were short-distance)
did not.

Planned investigation (future stage, not urgent): tune
SimpleGoalChecker / RegulatedPurePursuitController deceleration
interaction, or evaluate an alternate controller plugin (DWB, MPPI)
with different goal-approach behavior.