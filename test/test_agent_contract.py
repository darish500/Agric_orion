"""
test_agent_contract.py

Deterministic tests for the agent response validator. No ROS, no
network, no LLM -- these must pass in complete isolation, since this
validator is the safety boundary between untrusted model output and
Nav2. Every case here mirrors one of the manual test_cases originally
in agent_contract.py's __main__ block.
"""

import pytest

from agric_orion.agent_contract import validate_agent_response


# Each entry: (description, input_response, expected_ok, expected_result)
#
# - When expected_ok is True, expected_result is the full dict we expect
#   validate_agent_response to return -- not just "it passed."
# - When expected_ok is False, expected_result is a substring that must
#   appear in the returned reason string, not an exact match, so wording
#   tweaks later don't break the test suite.
CASES = [
    (
        "valid_named_location",
        {"action": "NAVIGATE", "target": {"location": "northern_inspection_point"},
         "reason": "Inspecting north field"},
        True,
        {"action": "NAVIGATE", "x": -3.0, "y": 3.0, "reason": "Inspecting north field"},
    ),
    (
        "valid_raw_coordinates",
        {"action": "NAVIGATE", "target": {"x": 1.0, "y": -1.0}},
        True,
        {"action": "NAVIGATE", "x": 1.0, "y": -1.0, "reason": ""},
    ),
    (
        "not_a_dict",
        "this is not a dict",
        False,
        "not a JSON object",
    ),
    (
        "none_response",
        None,
        False,
        "not a JSON object",
    ),
    (
        "missing_action",
        {"target": {"x": 0.0, "y": 0.0}},
        False,
        "missing required field: 'action'",
    ),
    (
        "unsupported_action",
        {"action": "SPIN_IN_PLACE", "target": {"x": 0.0, "y": 0.0}},
        False,
        "unsupported action",
    ),
    (
        "empty_target",
        {"action": "NAVIGATE", "target": {}},
        False,
        "target must contain either",
    ),
    (
        "target_wrong_type",
        {"action": "NAVIGATE", "target": {"x": "1.0", "y": "2.0"}},
        False,
        "target.x must be a number",
    ),
    (
        "target_out_of_bounds",
        {"action": "NAVIGATE", "target": {"x": 100.0, "y": 0.0}},
        False,
        "outside map bounds",
    ),
    (
        "unknown_location",
        {"action": "NAVIGATE", "target": {"location": "mars_base"}},
        False,
        "unknown location",
    ),
]


@pytest.mark.parametrize(
    "description, response, expected_ok, expected",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_validate_agent_response(description, response, expected_ok, expected):
    ok, result = validate_agent_response(response)

    assert ok is expected_ok, (
        f"[{description}] expected ok={expected_ok}, got ok={ok}, result={result!r}"
    )

    if expected_ok:
        assert result == expected, (
            f"[{description}] expected {expected!r}, got {result!r}"
        )
    else:
        assert expected in result, (
            f"[{description}] expected reason to contain {expected!r}, got {result!r}"
        )