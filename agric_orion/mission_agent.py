MOCK_RESPONSES = {
    "go to the northern inspection point": {
        "action": "NAVIGATE",
        "target": {"location": "northern_inspection_point"},
        "reason": "Northern inspection point selected as requested."
    },
    "inspect the southern section": {
        "action": "NAVIGATE",
        "target": {"location": "southern_inspection_point"},
        "reason": "Interpreted 'southern section' as the southern inspection point."
    },
    "move to the eastern side of the field": {
        "action": "NAVIGATE",
        "target": {"x": 50.0, "y": 0.0},
        "reason": "Estimated eastern edge of the field."
    },
    "what is the weather today": {
        "action": "CHAT",
        "reason": "This request is not a navigation mission."
    },

    "go to the eastern field point":{
        "action": "NAVIGATE",
        "target": {"location": "eastern_field_point"},
        "reason": "Eastern field point selected as requested."
    },
}


class MockNemotronAgent:
    def interpret_mission(self, mission_text, world_state=None):
        key = mission_text.strip().lower().rstrip(".?!")

        if key == "trigger simulated api failure":
            raise ConnectionError("Simulated Nemotron API failure (timeout)")

        

        # New: a world-state-aware decision, made BEFORE looking up the
        # mission response. This simulates the agent reasoning over
        # physical context, not just the mission text alone.
        if world_state is not None and world_state.get("path_blocked") is True:
            return {
                "action": "WAIT",
                "reason": (
                    "path_blocked is True in current world state; "
                    "holding off on issuing a new navigation objective."
                )
            }

        if key in MOCK_RESPONSES:
            return MOCK_RESPONSES[key]

        return {}