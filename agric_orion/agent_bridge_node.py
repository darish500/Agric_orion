import json

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose

from agric_orion.mission_agent import MockNemotronAgent
from agric_orion.agent_contract import validate_agent_response


class AgentBridgeNode(Node):
    def __init__(self):
        super().__init__('agent_bridge_node')

        self.agent = MockNemotronAgent()
        self.latest_world_state = None
        self.latest_vision_context = None

        self.declare_parameter('use_visual_evidence', True)
        self.declare_parameter('mission', 'Go to the northern inspection point.')
        self.declare_parameter('evidence_max_age_s', 1.5)
        self.declare_parameter('require_fresh_evidence', False)
        self.declare_parameter('vision_stop_hits', 2)
        self.declare_parameter('vision_resume_hits', 3)
        self.declare_parameter('lidar_explain_tol_m' , 0.6)

        self.latest_visual_evidence = None
        self.visual_evidence_received_at = None
        self.vision_hits = 0
        self.vision_clear_hits = 0
        self.vision_cancel_triggered = False
        self.waiting_on_vision = False

        self.world_state_sub = self.create_subscription(
            String, 'world_state', self.world_state_callback, 10)
        self.vision_context_sub = self.create_subscription(
            String, 'vision_context', self.vision_context_callback, 10)
        self.visual_evidence_sub = self.create_subscription(
            String, 'visual_evidence', self.visual_evidence_callback, 10)

        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        self.test_mission = self.get_parameter('mission').value
        self.mission_sent = False
        self.current_mission_text = None

        self.get_logger().info('agent_bridge_node started, waiting for world_state...')
        self.goal_in_progress = False
        self.active_goal_handle = None
        self.blocked_since = None
        self.reeval_triggered = False
        self.reeval_timer = self.create_timer(2.0, self.reevaluate_mission)

    # ---------- inputs ----------

    def world_state_callback(self, msg: String):
        try:
            self.latest_world_state = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError) as e:
            self.get_logger().error(f'Failed to parse world_state JSON: {e}')
            return

        evidence_ready = (not self.get_parameter('use_visual_evidence').value
                          or self.latest_visual_evidence is not None)
        if (not self.mission_sent and self.latest_vision_context is not None
                and evidence_ready):
            self.mission_sent = True
            self.run_mission(self.test_mission)

    def vision_context_callback(self, msg: String):
        try:
            self.latest_vision_context = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError) as e:
            self.get_logger().error(f'Failed to parse vision_context JSON: {e}')

    def visual_evidence_callback(self, msg: String):
        try:
            evidence = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError) as e:
            self.get_logger().error(f'Failed to parse visual_evidence JSON: {e}')
            return
        self.latest_visual_evidence = evidence
        self.visual_evidence_received_at = self.get_clock().now()
        self.update_vision_state(self.explain_with_lidar(evidence))

    def fresh_visual_evidence(self):
        if not self.get_parameter('use_visual_evidence').value:
            return None
        if self.latest_visual_evidence is None or self.visual_evidence_received_at is None:
            return None
        age = (self.get_clock().now() - self.visual_evidence_received_at).nanoseconds / 1e9
        if age > self.get_parameter('evidence_max_age_s').value:
            self.get_logger().warn(
                f'[AGENT BRIDGE] visual_evidence is stale ({age:.1f}s): '
                f'treated as unavailable, NOT as clear.')
            return None
        return self.explain_with_lidar(self.latest_visual_evidence)

    def explain_with_lidar(self, evidence):
        """Vision adds caution only for obstructions LiDAR cannot account for."""
        if evidence is None or evidence.get('visual_obstruction') is not True:
            return evidence
        ws = self.latest_world_state or {}
        lidar_m = ws.get('nearest_obstacle_m')
        vision_m = evidence.get('est_range_m')
        tol = self.get_parameter('lidar_explain_tol_m').value
        if lidar_m is not None and vision_m is not None and abs(lidar_m - vision_m) <= tol:
            self.get_logger().info(
                f'[VISION GUARD] obstruction at ~{vision_m} m is explained by LiDAR '
                f'(nearest {lidar_m:.2f} m); not adding a stop.',
                throttle_duration_sec=2.0)
            out = dict(evidence)
            out['visual_obstruction'] = False
            out['note'] = 'obstruction explained by LiDAR'
            return out
        return evidence

    # ---------- vision guard: stop while driving, resume when clear ----------

    def update_vision_state(self, evidence):
        if not self.get_parameter('use_visual_evidence').value:
            return
        obstructed = evidence.get('visual_obstruction') is True

        if self.goal_in_progress:
            self.vision_hits = self.vision_hits + 1 if obstructed else 0
            need = self.get_parameter('vision_stop_hits').value
            if obstructed:
                self.get_logger().info(
                    f'[VISION GUARD] obstruction seen ({self.vision_hits}/{need}), '
                    f'range ~{evidence.get("est_range_m")} m')
            if self.vision_hits >= need and not self.vision_cancel_triggered:
                self.vision_cancel_triggered = True
                self.waiting_on_vision = True
                self.vision_clear_hits = 0
                self.get_logger().warn(
                    '[AGENT RE-EVAL] OpenCV reports an obstruction during an active goal '
                    '-- cancelling the goal to re-evaluate the mission.')
                self.cancel_and_reevaluate()

        elif self.waiting_on_vision:
            self.vision_clear_hits = 0 if obstructed else self.vision_clear_hits + 1
            need = self.get_parameter('vision_resume_hits').value
            if self.vision_clear_hits >= need:
                self.waiting_on_vision = False
                self.vision_clear_hits = 0
                self.get_logger().info(
                    '[AGENT RE-EVAL] OpenCV evidence has been clear again -- '
                    're-running the mission.')
                if self.current_mission_text is not None:
                    self.run_mission(self.current_mission_text)

    # ---------- agent / validator / Nav2 ----------

    def run_mission(self, mission_text):
        self.current_mission_text = mission_text

        self.get_logger().info(f'[AGENT BRIDGE] Mission: "{mission_text}"')
        evidence = self.fresh_visual_evidence()
        self.get_logger().info(f'[AGENT BRIDGE] visual_evidence passed to agent: {evidence}')

        if (self.get_parameter('use_visual_evidence').value
                and self.get_parameter('require_fresh_evidence').value
                and evidence is None):
            self.get_logger().warn(
                '[AGENT BRIDGE] OpenCV evidence is required but missing or stale: '
                'WAIT (fail-closed). Nothing sent to Nav2.')
            return

        try:
            raw_response = self.agent.interpret_mission(
                mission_text,
                world_state=self.latest_world_state,
                vision_context=self.latest_vision_context,
                visual_evidence=evidence)
        except Exception as e:
            self.get_logger().error(
                f'[AGENT BRIDGE] Agent call failed: {e}. Nothing sent to Nav2.')
            return

        self.get_logger().info(f'[MOCK AGENT] raw response: {raw_response}')

        is_valid, result = validate_agent_response(raw_response)
        self.get_logger().info(f'[VALIDATOR] valid={is_valid} -> {result}')

        if not is_valid:
            self.get_logger().warn(
                f'[AGENT BRIDGE] Response REJECTED, nothing sent to Nav2. Reason: {result}')
            return

        if result['action'] == 'WAIT':
            self.get_logger().info(
                f'[AGENT BRIDGE] Agent chose WAIT, nothing sent to Nav2. Reason: {result["reason"]}')
            return

        if result['action'] == 'NAVIGATE':
            self.send_navigate_goal(result['x'], result['y'], result['reason'])
            return

        self.get_logger().error(
            f'[AGENT BRIDGE] Validated result has unhandled action: {result["action"]}')

    def send_navigate_goal(self, x, y, reason):
        self.get_logger().info(
            f'[AGENT BRIDGE] Sending NavigateToPose goal: ({x}, {y}) -- reason: "{reason}"')

        self.nav_client.wait_for_server()

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.orientation.w = 1.0

        send_goal_future = self.nav_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f'[NAV2 FEEDBACK] distance_remaining={feedback.distance_remaining:.2f}m, '
            f'recoveries={feedback.number_of_recoveries}',
            throttle_duration_sec=2.0)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('[AGENT BRIDGE] Nav2 REJECTED the goal.')
            return

        self.get_logger().info('[AGENT BRIDGE] Nav2 accepted the goal.')
        self.goal_in_progress = True
        self.active_goal_handle = goal_handle
        self.vision_hits = 0
        self.vision_cancel_triggered = False
        self.waiting_on_vision = False
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        result = future.result()
        status = result.status
        status_names = {4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}
        self.get_logger().info(
            f'[AGENT BRIDGE] Nav2 goal finished: {status_names.get(status, status)}')

        self.goal_in_progress = False
        self.active_goal_handle = None
        self.blocked_since = None
        self.reeval_triggered = False

    # ---------- LiDAR-based sustained-blockage re-evaluation (unchanged) ----------

    def reevaluate_mission(self):
        if not self.goal_in_progress or self.latest_world_state is None:
            return

        path_blocked = self.latest_world_state.get('path_blocked', False)
        now = self.get_clock().now()

        if path_blocked:
            if self.blocked_since is None:
                self.blocked_since = now
            else:
                blocked_duration = (now - self.blocked_since).nanoseconds / 1e9
                if blocked_duration > 8.0 and not self.reeval_triggered:
                    self.reeval_triggered = True
                    self.get_logger().warn(
                        f'[AGENT RE-EVAL] path_blocked for {blocked_duration:.1f}s during '
                        f'active goal -- cancelling current goal to re-evaluate the mission.'
                    )
                    self.cancel_and_reevaluate()
        else:
            self.blocked_since = None
            self.reeval_triggered = False

    def cancel_and_reevaluate(self):
        if self.active_goal_handle is None:
            return

        cancel_future = self.active_goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(self.cancel_done_callback)

    def cancel_done_callback(self, future):
        cancel_response = future.result()

        if len(cancel_response.goals_canceling) > 0:
            self.get_logger().info(
                '[AGENT RE-EVAL] Nav2 confirmed the goal was cancelled. '
                'Re-evaluating mission with current context.')
        else:
            self.get_logger().warn(
                '[AGENT RE-EVAL] Cancel request returned no goals cancelling '
                '-- goal may have already finished on its own.')

        self.goal_in_progress = False
        self.active_goal_handle = None

        if self.current_mission_text is not None:
            self.run_mission(self.current_mission_text)


def main(args=None):
    rclpy.init(args=args)
    node = AgentBridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()