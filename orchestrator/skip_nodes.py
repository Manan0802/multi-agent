import json
from typing import Dict, Any
from orchestrator.state import OrchestratorState
from orchestrator.nodes import format_skip

def skip_web_search(state: OrchestratorState) -> Dict:
    return {"thought_stream": [format_skip("web_search (Gate 0) — External supplement not needed.")]}

def skip_world_knowledge(state: OrchestratorState) -> Dict:
    return {"thought_stream": [format_skip("world_knowledge (Gate 0b) — No conflicts detected.")]}

def skip_missing_spec(state: OrchestratorState) -> Dict:
    return {"thought_stream": [format_skip("missing_spec_agent (Gate 1) — no buyer signal and no world knowledge fallback available.")]}

def skip_sequencing(state: OrchestratorState) -> Dict:
    return {"thought_stream": [format_skip("sequencing_agent (Gate 2) — fewer than 2 real signals. Rankings would be unreliable.")]}

def skip_option(state: OrchestratorState) -> Dict:
    return {"thought_stream": [format_skip("option_agent (Gate 3) — no specs with options found to evaluate.")]}
