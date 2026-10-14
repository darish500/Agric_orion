class GuardedAgent:
    """Wraps any agent. LiDAR or OpenCV can force WAIT; nothing can clear a block."""

    def __init__(self, inner):
        self.inner = inner

    def interpret_mission(self, mission_text, world_state=None,
                          vision_context=None, visual_evidence=None):
        response = self.inner.interpret_mission(
            mission_text,
            world_state=world_state,
            vision_context=vision_context,
            visual_evidence=visual_evidence)

        # Only a NAVIGATE proposal can be overridden. Anything else passes
        # through unchanged (WAIT, malformed output; the validator handles those).
        if not isinstance(response, dict) or response.get('action') != 'NAVIGATE':
            return response

        lidar_blocked = world_state is not None and world_state.get('path_blocked') is True
        opencv_blocked = (visual_evidence is not None
                          and visual_evidence.get('visual_obstruction') is True)

        if lidar_blocked:
            return {'action': 'WAIT',
                    'reason': 'guard override: LiDAR path_blocked is True.', 
                    'agent_proposed': response}
        if opencv_blocked:
            return {'action': 'WAIT',
                    'reason': 'guard override: OpenCV reports a visual obstruction.',
                    'agent_proposed': response}
        return response