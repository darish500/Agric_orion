import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agric_orion'))

from bedrock_agent import BedrockAgent
from agent_contract import validate_agent_response

agent = BedrockAgent('global.amazon.nova-2-lite-v1:0')

missions = [
    "Go to the field centre.",
    "Go to the northern inspection point.",
    "What is the weather today?",
    "Move to the eastern side of the field.",
]

for mission in missions:
    raw = agent.interpret_mission(mission)
    ok, result = validate_agent_response(raw)
    print(mission)
    print('   raw      :', raw)
    print('   validator:', ok)