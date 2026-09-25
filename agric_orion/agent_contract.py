"""
agent_contract.py

Pure Python validation layer for Nemotron agent responses. No ROS, no
network, no LLM dependency here on purpose -- this must be testable in
complete isolation, deterministically, before any real model is
connected. Treat every input to validate_agent_response() as untrusted,
exactly like sanitizing external input in any secure system.
"""

# Known, pre-vetted named locations. Each one is trusted by construction --
# if a name is in this table, its coordinates need no further bounds
# checking. Add new locations here deliberately, never from LLM output.
KNOWN_LOCATIONS = {
    "northern_inspection_point": (-3.0, 3.0),
    "home_base": (-3.0, 0.0),
    "eastern_field_point": (5.0 , 0.0)
}

# The actual physical extent of the known map (from generate_map.py's
# world_min_x/max_x/min_y/max_y). Any raw x/y target must fall inside
# this box.
MAP_BOUNDS = {
    "x_min": -6.0, "x_max": 6.0,
    "y_min": -6.0, "y_max": 6.0,
}

ALLOWED_ACTIONS = {"NAVIGATE", "WAIT"}


def validate_agent_response(response):
    """
    Validate a hypothetical agent (LLM) response.

    Args:
        response: whatever the agent produced, already parsed from JSON
                   into a Python object (could be anything -- dict, list,
                   string, None, etc. -- never assume it's well-formed).

    Returns:
        (True, validated_objective_dict) if valid
        (False, reason_string) if invalid -- never raises an exception.
    """
    # --- Top-level shape check ---
    if not isinstance(response, dict):
        return False, f"response is not a JSON object (got {type(response).__name__})"

    # --- Action field ---
    action = response.get("action")
    if action is None:
        return False, "missing required field: 'action'"
    if not isinstance(action, str):
        return False, f"'action' must be a string (got {type(action).__name__})"
    if action not in ALLOWED_ACTIONS:
        return False, f"unsupported action: '{action}'"

    if action == "WAIT":
        reason = response.get("reason", "")
        if reason is not None and not isinstance(reason, str):
            return False, f"'reason' must be a string if present (got {type(reason).__name__})"
        return True, {"action": "WAIT", "reason": reason if isinstance(reason, str) else ""}

    # --- NAVIGATE-specific validation ---
    if action == "NAVIGATE":
        target = response.get("target")
        if target is None:
            return False, "missing required field: 'target'"
        if not isinstance(target, dict):
            return False, f"'target' must be an object (got {type(target).__name__})"

        x = None
        y = None

        if "location" in target:
            location = target["location"]
            if not isinstance(location, str):
                return False, f"'location' must be a string (got {type(location).__name__})"
            if location not in KNOWN_LOCATIONS:
                return False, f"unknown location: '{location}'"
            x, y = KNOWN_LOCATIONS[location]

        elif "x" in target and "y" in target:
            raw_x = target["x"]
            raw_y = target["y"]

            if not isinstance(raw_x, (int, float)) or isinstance(raw_x, bool):
                return False, f"target.x must be a number (got {type(raw_x).__name__})"
            if not isinstance(raw_y, (int, float)) or isinstance(raw_y, bool):
                return False, f"target.y must be a number (got {type(raw_y).__name__})"

            if not (MAP_BOUNDS["x_min"] <= raw_x <= MAP_BOUNDS["x_max"]):
                return False, f"target.x={raw_x} is outside map bounds"
            if not (MAP_BOUNDS["y_min"] <= raw_y <= MAP_BOUNDS["y_max"]):
                return False, f"target.y={raw_y} is outside map bounds"

            x, y = float(raw_x), float(raw_y)

        else:
            return False, "target must contain either 'location' or both 'x' and 'y'"

        # --- Optional reason field ---
        reason = response.get("reason", "")
        if reason is not None and not isinstance(reason, str):
            return False, f"'reason' must be a string if present (got {type(reason).__name__})"

        return True, {
            "action": "NAVIGATE",
            "x": x,
            "y": y,
            "reason": reason if isinstance(reason, str) else "",
        }

    # Unreachable given ALLOWED_ACTIONS check above, but kept for safety.
    return False, f"unhandled action: '{action}'"


if __name__ == "__main__":
    test_cases = [
        # Valid: named location
        {"action": "NAVIGATE", "target": {"location": "northern_inspection_point"},
         "reason": "Inspecting north field"},

        # Valid: raw coordinates
        {"action": "NAVIGATE", "target": {"x": 1.0, "y": -1.0}},

        # Malformed: not a dict at all
        "this is not a dict",

        # Malformed: None
        None,

        # Missing 'action'
        {"target": {"x": 0.0, "y": 0.0}},

        # Unsupported action
        {"action": "SPIN_IN_PLACE", "target": {"x": 0.0, "y": 0.0}},

        # target with neither location nor x/y
        {"action": "NAVIGATE", "target": {}},

        # x/y wrong type (strings instead of numbers)
        {"action": "NAVIGATE", "target": {"x": "1.0", "y": "2.0"}},

        # x/y outside map bounds
        {"action": "NAVIGATE", "target": {"x": 100.0, "y": 0.0}},

        # unknown location name
        {"action": "NAVIGATE", "target": {"location": "mars_base"}},
    ]

    for case in test_cases:
        result = validate_agent_response(case)
        print(f"Input: {case}\n  -> {result}\n")