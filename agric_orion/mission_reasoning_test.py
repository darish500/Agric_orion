from mission_agent import MockNemotronAgent
from agent_contract import validate_agent_response

# Two hand-written sample world states -- no ROS involved yet.
WORLD_STATE_CLEAR = {
    "position": {"x": -3.0, "y": 0.0},
    "yaw": 0.0,
    "nearest_obstacle_m": 4.2,
    "path_blocked": False,
}

WORLD_STATE_BLOCKED = {
    "position": {"x": 1.2, "y": 0.1},
    "yaw": 0.02,
    "nearest_obstacle_m": 0.4,
    "path_blocked": True,
}

TEST_CASES = [
    ("Go to the northern inspection point.", WORLD_STATE_CLEAR),
    ("Go to the northern inspection point.", WORLD_STATE_BLOCKED),
    ("Inspect the southern section.", WORLD_STATE_CLEAR),
    ("Move to the eastern side of the field.", WORLD_STATE_CLEAR),
    ("What is the weather today?", WORLD_STATE_CLEAR),
    ("Do a backflip.", WORLD_STATE_CLEAR),
]

if __name__ == "__main__":
    agent = MockNemotronAgent()

    for mission, world_state in TEST_CASES:
        print(f"\nMission: \"{mission}\"  (path_blocked={world_state['path_blocked']})")

        raw_response = agent.interpret_mission(mission, world_state=world_state)
        print(f"  [MOCK AGENT] raw response: {raw_response}")

        is_valid, result = validate_agent_response(raw_response)
        print(f"  Validation result: valid={is_valid} -> {result}")