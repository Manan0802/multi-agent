import sys
import os
import traceback

# Ensure the LLM gateway key is present for any process (including Streamlit)
os.environ.setdefault("LLM_GATEWAY_API_KEY", "sk-PbMyg_3D9EM-yaaEVRVbXA")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from orchestrator.graph_builder import build_graph

def run_orchestrator(mcat_id: str, category_name: str):
    # Safety: Strip any whitespace that might cause [Errno 22] in URL sockets on Windows
    mcat_id = str(mcat_id).strip()
    category_name = str(category_name).strip()
    
    print(f"--- Starting Orchestrator for MCAT: {mcat_id} ({category_name}) ---")
    
    app = build_graph()
    
    initial_state = {
        "mcat_id": mcat_id,
        "category_name": category_name,
        "ds1_status": "EMPTY",
        "ds2_status": "EMPTY",
        "ds3_status": "EMPTY",
        "ds4_status": "EMPTY",
        "ds1_data": [],
        "ds2_data": [],
        "ds3_data": [],
        "ds4_data": [],
        "availability_map": {},
        "thought_stream": [],
        "web_search_result": {},
        "world_knowledge_result": {},
        "missing_specs_output": {},
        "sequenced_specs": {},
        "final_options": {},
        "final_output": {}
    }
    
    try:
        # Removed manual reconfigure as it clashes with Streamlit's internal buffers
            
        final_state = app.invoke(initial_state)
        print("\n--- Pipeline Thought Stream ---")
        import re
        # This regex removes control characters (0-31 and 127) but allows all other Unicode (including Hindi, Emojis, etc.)
        control_chars_pattern = re.compile(r'[\x00-\x1F\x7F]')
        
        for thought in final_state.get("thought_stream", []):
            try:
                # Safe print: Scrub ONLY the control chars that trigger Errno 22, allow full Unicode
                t_raw = str(thought)
                t_clean = control_chars_pattern.sub('', t_raw)
                
                if len(t_clean) > 1500:
                    print(t_clean[:1500] + "... [TRUNCATED FOR CONSOLE]")
                else:
                    print(t_clean)
            except:
                pass
        return final_state
    except Exception as e:
        print(f"Error during execution: {traceback.format_exc()}")
        return {"final_output": {"Summary": f"Failed with error: {str(e)}"}}

if __name__ == "__main__":
    run_orchestrator("191595", "Industrial Machinery")
