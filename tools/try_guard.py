import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agric_orion'))

from agent_guard import GuardedAgent


class AlwaysNavigate:
    """A fake agent that ignores every block, like a careless model might."""
    def interpret_mission(self, mission_text, world_state=None,
                          vision_context=None, visual_evidence=None):
        return {'action': 'NAVIGATE', 'target': {'x': 0, 'y': 0}, 'reason': 'fake'}


class AlwaysWait:
    def interpret_mission(self, mission_text, world_state=None,
                          vision_context=None, visual_evidence=None):
        return {'action': 'WAIT', 'reason': 'fake'}


nav = GuardedAgent(AlwaysNavigate())
wait = GuardedAgent(AlwaysWait())

print('1 clear, clear       :', nav.interpret_mission('x', {'path_blocked': False}, None, {'visual_obstruction': False})['action'])
print('2 LiDAR blocked      :', nav.interpret_mission('x', {'path_blocked': True}, None, {'visual_obstruction': False})['action'])
print('3 OpenCV obstructed  :', nav.interpret_mission('x', {'path_blocked': False}, None, {'visual_obstruction': True})['action'])
print('4 both blocked       :', nav.interpret_mission('x', {'path_blocked': True}, None, {'visual_obstruction': True})['action'])
print('5 evidence missing   :', nav.interpret_mission('x', {'path_blocked': False}, None, None)['action'])
print('6 agent says WAIT    :', wait.interpret_mission('x', {'path_blocked': False}, None, {'visual_obstruction': False})['action'])