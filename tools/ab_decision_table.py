import glob, json, os, sys
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from agric_orion.detect_obstruction import detect
from agric_orion.mission_agent import MockNemotronAgent
from agric_orion.agent_contract import validate_agent_response

DATA = os.path.expanduser('~/workspace/stage6_data')
MISSION = "Go to the eastern field point."
agent = MockNemotronAgent()

def decide(world_state, evidence):
    raw = agent.interpret_mission(MISSION, world_state=world_state, visual_evidence=evidence)
    ok, result = validate_agent_response(raw)
    return (result['action'] if ok else 'REJECTED')

print(f'{"scenario":13s} lidar_min  lidar_blk  opencv  CaseA(LiDAR only)  CaseB(+OpenCV)')
for jp in sorted(glob.glob(os.path.join(DATA, '*.json'))):
    name = os.path.basename(jp)[:-5]
    png = os.path.join(DATA, name + '.png')
    if not os.path.exists(png):
        continue
    fmin = json.load(open(jp))['forward_min_m']
    ws = {'path_blocked': fmin is not None and fmin < 1.0}
    ev = detect(cv2.imread(png))
    a, b = decide(ws, None), decide(ws, ev)
    flag = '  <-- decision changed' if a != b else ''
    print(f'{name:13s} {fmin!s:9.9s} {ws["path_blocked"]!s:9s}  {ev["visual_obstruction"]!s:6s}  {a:17s}  {b}{flag}')