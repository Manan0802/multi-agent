from typing import TypedDict, Annotated, List, Dict, Any
import operator

class OrchestratorState(TypedDict):
    mcat_id: str
    category_name: str
    
    # Store outputs of Phase 1 Parallel fetch
    ds0_status: str
    ds1_status: str
    ds2_status: str
    ds3_status: str
    ds4_status: str
    ds5_status: str
    
    ds0_data: List[Dict]
    ds1_data: List[Dict]
    ds2_data: List[Dict]
    ds3_data: List[Dict]
    ds4_data: List[Dict]
    ds5_data: List[Dict]
    
    # Store AI analysis from individual DS agents
    ds1_agent_output: Dict[str, Any]
    ds2_agent_output: Dict[str, Any]
    ds3_agent_output: Dict[str, Any]
    
    # Availability Map with Reducer to allow concurrent updates from parallel fetchers
    availability_map: Annotated[Dict[str, str], operator.ior]
    
    # Trace for final audit
    final_audit_results: List[Dict]
    
    # Track the pipeline thought stream linearly
    thought_stream: Annotated[List[str], operator.add]
    
    # Web search and world knowledge results
    web_search_result: Dict[str, Any]
    world_knowledge_result: Dict[str, Any]
    
    # Agent outputs
    missing_specs_output: Dict[str, Any]
    sequenced_specs: Dict[str, Any]
    final_options: Dict[str, Any]
    
    # Master Orchestrator Fields
    gate_decisions: Dict[str, Any]
    master_wk_tasks: List[str]
    master_ws_queries: List[str]
    master_overrides: List[str]
    master_anomalies: List[str]
    master_confidence: str
    master_raw_response: str
    
    final_output: Dict[str, Any]
