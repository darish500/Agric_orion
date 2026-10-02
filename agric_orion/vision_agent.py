"""
Mock vision reasoning agent for Stage 5.

Mirrors the MockNemotronAgent pattern from Stage 4: implements the
exact interface a real vision-language agent will need to satisfy, so
every downstream consumer (a future vision_context_node, and
eventually the mission agent itself) can be built and tested now,
without live access to any real vision model.

Real integration point (once live access is available -- Gemini via
Roboflow, or otherwise): a RoboflowVisionAgent class implementing this
identical describe_scene() signature. Swapping
self.vision_agent = MockVisionAgent() for
self.vision_agent = RoboflowVisionAgent() is the entire remaining step,
exactly as documented for NemotronAgent in the Stage 4 summary.
"""

SCENARIO_RESPONSES = {
    'obstacle_ahead': {
        'description': (
            "Two large obstacles sit side by side directly ahead, "
            "with a narrow gap between them too tight to pass through. "
            "Green posts are visible behind them."
        ),
        'path_looks_blocked' : True, 
    },


    'crop_row': {
        'description': (
            "Two upright green posts stand ahead on open ground, "
            "consistent with a crop row rather than an obstacle."
        ),
        'path_looks_blocked': False,
    },

    'open_field': {
        'description': (
            "Open, flat ground ahead. A distant boundary wall is "
            "visible on the horizon but is not a near-term obstruction."
        ),
        'path_looks_blocked': False,
    },


    'partially_obstructed': {
        'description': (
              "A large obstacle sits off to one side. There is a clear, "
            "open lane to the other side of it."
        ),
        'path_looks_blocked': False,
    },

    'changed_scene': {
        'description': (
            "A new large object has appeared close to the vehicle, "
            "casting a shadow, where the previous frame showed open "
            "ground."
        ),
        'path_looks_blocked': True
    }
}


DEFAULT_SCENARIO = 'open_field'

class MockVisionAgent:

    def describe_scene(self , image , scenario_hint = None):
        if scenario_hint is None or scenario_hint not in SCENARIO_RESPONSES:

            scenario_hint = DEFAULT_SCENARIO

        response = SCENARIO_RESPONSES[scenario_hint]

        return {
            'description': response['description'],
            'path_looks_blocked': response['path_looks_blocked'],
            'source': 'mock',
            'scenario': scenario_hint,
        }


def main(): 
    agent = MockVisionAgent()

    for scenario in list (SCENARIO_RESPONSES.keys()) + [None , 'not_a_real_scenario']:
        result = agent.describe_scene(image= None , scenario_hint=scenario)
        print(f'scenario_hint = {scenario!r} -> {result}')



if __name__== '__main__':
    main()

