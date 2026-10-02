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


def _vision_note(vision_context):
    """
    Builds a short, honest phrase describing what the vision layer
    reported, for appending to a decision's 'reason' field. Always
    names the source explicitly (mock vs real) so nothing downstream
    can mistake a mock judgment for a real one -- same principle as
    MockVisionAgent's own 'source' field.

    Returns None if there is nothing usable to report, so callers can
    skip appending anything rather than adding an empty note.
    """
    if not vision_context:
        return None

    description = vision_context.get('description')
    source = vision_context.get('source', 'unknown')

    if not description:
        return None

    return f"[vision context, source={source}]: {description}"


class MockNemotronAgent:
    def interpret_mission(self, mission_text, world_state=None, vision_context=None):
        key = mission_text.strip().lower().rstrip(".?!")

        if key == "trigger simulated api failure":
            raise ConnectionError("Simulated Nemotron API failure (timeout)")

        vision_note = _vision_note(vision_context)
        vision_says_blocked = (
            vision_context.get('path_looks_blocked') if vision_context else None
        )

        # LiDAR-grounded world_state remains authoritative for the
        # blocked/not-blocked decision -- see docs/stage5_vision_experiment.md
        # for why: vision was shown, with real evidence, to misjudge
        # near-vs-far without a distance measurement, while LiDAR
        # never has. Vision context enriches the *reason* given for a
        # decision; it does not get a vote on the decision itself.
        if world_state is not None and world_state.get("path_blocked") is True:
            reason = (
                "path_blocked is True in current world state; "
                "holding off on issuing a new navigation objective."
            )
            if vision_note is not None:
                if vision_says_blocked is False:
                    # Honest disagreement: LiDAR still wins, but this
                    # is worth surfacing, not hiding.
                    reason += (
                        f" Note: vision context did not flag an obstruction "
                        f"({vision_note}), but LiDAR-based path_blocked takes "
                        f"priority."
                    )
                else:
                    reason += f" {vision_note}"
            return {
                "action": "WAIT",
                "reason": reason,
            }

        if key in MOCK_RESPONSES:
            response = dict(MOCK_RESPONSES[key])  # shallow copy, don't mutate the shared dict
            if vision_note is not None:
                extra = vision_note
                if vision_says_blocked is True:
                    # LiDAR says clear, but vision flagged something.
                    # Action does not change (LiDAR remains
                    # authoritative for safety), but this is
                    # surfaced honestly in the reason, not silently
                    # dropped.
                    extra = (
                        f"Proceeding on LiDAR-grounded clearance, though "
                        f"{vision_note}"
                    )
                response["reason"] = f"{response['reason']} {extra}"
            return response

        return {}