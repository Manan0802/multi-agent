import json
import re
from typing import Dict, Any, List
from orchestrator.state import OrchestratorState
from orchestrator.llm_client import stream_llm, extract_json
from orchestrator.nodes import get_api_key, format_thought, format_result, format_skip, format_thinking
from orchestrator.prompts import MASTER_ORCHESTRATOR_SYSTEM_PROMPT

def _classify_ds(result: List[Dict]) -> str:
    """Classifies one DS result dict as RICH / SPARSE / EMPTY"""
    if not result:
        return "EMPTY"
    
    # We use roughly the same thresholds as evaluate_ds* in data_loader.py
    # but here we are looking at the pre-fetched data in state.
    count = len(result)
    
    # Check if results are actually meaningful (not just a record that it was empty)
    if count == 0:
        return "EMPTY"
    if count < 3: # Generic heuristic for SPARSE
        return "SPARSE"
    return "RICH"


def master_orchestrator_node(state: OrchestratorState) -> Dict:
    cat_name = state.get("category_name", "Unknown")
    mcat_id = state.get("mcat_id", "Unknown")
    
    # Ground Truth Statuses from Data Loader
    ds1_status = state.get("ds1_status") or "EMPTY"
    ds2_status = state.get("ds2_status") or "EMPTY"
    ds3_status = state.get("ds3_status") or "EMPTY"
    ds4_status = state.get("ds4_status") or "EMPTY"
    ds5_status = state.get("ds5_status") or "EMPTY"
    
    # Compact DS-0 Summary for reasoning depth
    ds0 = state.get("ds0_data") or []
    ds0_compact = [{"name": s.get("spec_name"), "tier": s.get("tier")} for s in ds0]
    
    ds1 = state.get("ds1_data") or []
    ds2 = state.get("ds2_data") or []
    ds3 = state.get("ds3_data") or []
    ds4 = state.get("ds4_data") or []
    ds5 = state.get("ds5_data") or []
    
    user_prompt = f"Category: {cat_name}\nMCAT ID: {mcat_id}\n\n"
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += "DATA SOURCE RICHNESS (GROUND TRUTH - DO NOT OVERRIDE)\n"
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += f"DS-1 Buyer Calls: {ds1_status}\n"
    user_prompt += f"DS-2 Custom Specs: {ds2_status}\n"
    user_prompt += f"DS-3 Buyer Search: {ds3_status}\n"
    user_prompt += f"DS-4 Fill Rate: {ds4_status}\n"
    user_prompt += f"DS-5 Option Fill Rate: {ds5_status}\n\n"
    
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += "THE BASELINE: PLATFORM SPECS (DS-0)\n"
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += f"{json.dumps(ds0_compact, indent=2)}\n\n"
    
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += "AUDIT DATA: RAW SIGNALS (DS 1-5)\n"
    user_prompt += "──────────────────────────────────────────────────────────────────────\n"
    user_prompt += f"DS-1 Buyer-Seller Call Data: {len(ds1)} records. Sample: {json.dumps(ds1[:3])}\n"
    user_prompt += f"DS-2 Custom Specs Data: {len(ds2)} records. Sample: {json.dumps(ds2[:3])}\n"
    user_prompt += f"DS-3 Buyer Search Data: {len(ds3)} records. Sample: {json.dumps(ds3[:3])}\n"
    user_prompt += f"DS-4 Product Fill Rate: {len(ds4)} records. Sample: {json.dumps(ds4[:3])}\n"
    user_prompt += f"DS-5 Option-Level Market Data: {len(ds5)} records. Sample: {json.dumps(ds5[:3])}\n"
    
    thoughts = []
    full_response = ""
    current_buffer = ""
    
    try:
        thoughts.append(format_thinking(f"Analyzing {cat_name} (MCAT {mcat_id})... auditing signals against baseline."))
        
        # Call streaming LLM
        for chunk in stream_llm(get_api_key(), MASTER_ORCHESTRATOR_SYSTEM_PROMPT, user_prompt, model="google/gemini-2.5-pro"):
            full_response += chunk
            current_buffer += chunk
            
            if "\n" in current_buffer:
                lines = current_buffer.split("\n")
                for line in lines[:-1]:
                    l = line.strip()
                    # Flexible Tag Parsing: Catch tags even with leading markdown chars
                    tags = ["THINKING", "THOUGHT", "RESULT", "SKIP", "ANOMALY", "OVERRIDE", "WK-CALL", "WS-CALL", "DECISION"]
                    pattern = r"\[(" + "|".join(tags) + r")\].*"
                    if re.search(pattern, l, re.IGNORECASE):
                        thoughts.append(l)
                current_buffer = lines[-1]
                
        l = current_buffer.strip()
        tags = ["THINKING", "THOUGHT", "RESULT", "SKIP", "ANOMALY", "OVERRIDE", "WK-CALL", "WS-CALL", "DECISION"]
        pattern = r"\[(" + "|".join(tags) + r")\].*"
        if re.search(pattern, l, re.IGNORECASE):
            thoughts.append(l)
            
        parsed = extract_json(full_response)
        if not parsed or "gate_decisions" not in parsed:
            raise ValueError("Invalid Master JSON")
            
        g_dec = parsed.get("gate_decisions", {})
        
        # We enforce our hardcoded availability map regardless of what the LLM says
        amap = {
            "DS-1 Buyer-Seller Call Data": ds1_status,
            "DS-2 Custom Specs Data": ds2_status,
            "DS-3 Buyer Search Data": ds3_status,
            "DS-4 Product Fill Rate": ds4_status,
            "DS-5 Option Fill Rate": ds5_status
        }
        
        # MANDATORY BUSINESS LOGIC OVERRIDES
        if ds1_status == "RICH" or ds2_status == "RICH":
            g_dec["gate_1_missing_spec"] = {"run": True, "reason": "OVERRIDE: Rich buyer/custom signals require gap audit"}
            g_dec["gate_2_sequencing"] = {"run": True, "reason": "OVERRIDE: Sequence audit required for new specs"}
            g_dec["gate_3_option"] = {"run": True, "reason": "OVERRIDE: Option audit required for integrity"}

        return {
            "availability_map": amap,
            "gate_decisions": g_dec,
            "thought_stream": thoughts,
            "master_wk_tasks": parsed.get("wk_tasks", []),
            "master_ws_queries": parsed.get("ws_queries", []),
            "master_overrides": parsed.get("overrides", []),
            "master_anomalies": parsed.get("anomalies", []),
            "master_confidence": parsed.get("confidence", "LOW"),
            "master_raw_response": full_response
        }
        
    except Exception as e:
        # Stop everything and show the raw truth. 
        # We need to see exactly what the model returned to fix the parsing logic.
        thoughts.append(format_result(f"CRITICAL: Master Orchestrator failed or returned invalid JSON."))
        thoughts.append(f"[ANOMALY] Error Trace: {str(e)}")
        
        if full_response:
            # Output the full response for absolute transparency in debugging
            thoughts.append(format_thought("DEBUG: Displaying FULL raw response from Gemini 2.5 Pro below:"))
            # Break it into chunks so it shows up in the dashboard stream
            parts = [full_response[i:i+800] for i in range(0, len(full_response), 800)]
            for p in parts:
                thoughts.append(f"|RAW| {p}")
            
        # FAILSAFE: If the LLM master fails, we decide to run the basic audit anyway
        failsafe_decisions = {
            "gate_0_web_search": {"run": False, "reason": "Failsafe mode: skipping web search"},
            "gate_1_missing_spec": {"run": True, "reason": "Failsafe mode: force-running missing spec gaps"},
            "gate_2_sequencing": {"run": True, "reason": "Failsafe mode: force-running sequencing"},
            "gate_3_option": {"run": True, "reason": "Failsafe mode: force-running option audit"}
        }
        
        # Create a basic amap from state
        amap = {
            "DS-1 Buyer-Seller Call Data": state.get("ds1_status", "EMPTY"),
            "DS-2 Custom Specs Data": state.get("ds2_status", "EMPTY"),
            "DS-3 Buyer Search Data": state.get("ds3_status", "EMPTY"),
            "DS-4 Product Fill Rate": state.get("ds4_status", "EMPTY"),
            "DS-5 Option Fill Rate": state.get("ds5_status", "EMPTY")
        }
        
        return {
            "availability_map": amap,
            "gate_decisions": failsafe_decisions, 
            "thought_stream": thoughts,
            "master_anomalies": [f"PARSING_FAILURE: {str(e)}"],
            "master_raw_response": full_response,
            "error_flag": True 
        }
