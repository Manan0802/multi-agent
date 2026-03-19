from langgraph.graph import StateGraph, START, END
from typing import Sequence

from orchestrator.state import OrchestratorState
from orchestrator.nodes import (
    orchestrator_init,
    fetch_ds1, fetch_ds2, fetch_ds3, fetch_ds4, fetch_ds5,
    join_all_sources,
    gate_0_web_search,
    gate_0b_world_knowledge,
    gate_1_missing_spec,
    gate_2_sequencing,
    gate_3_option,
    gate_4_post_audit_verification,
    output_assembly
)
from orchestrator.master_orchestrator_node import master_orchestrator_node
from orchestrator.skip_nodes import (
    skip_web_search, skip_world_knowledge, skip_missing_spec, skip_sequencing, skip_option
)

def _should_run(state, gate_name):
    decisions = state.get("gate_decisions", {})
    # default False = STRICT: only run if Master explicitly ordered it.
    return decisions.get(gate_name, {}).get("run", False) 

def gate_0_router(state: OrchestratorState) -> str:
    return "gate_0_web_search" if _should_run(state, "gate_0_web_search") else "skip_web_search"

def gate_0b_router(state: OrchestratorState) -> str:
    run_pre = _should_run(state, "pre_step_world_knowledge")
    run_0b = _should_run(state, "gate_0b_world_knowledge")
    return "gate_0b_world_knowledge" if (run_pre or run_0b) else "skip_world_knowledge"

def gate_1_router(state: OrchestratorState) -> str:
    return "gate_1_missing_spec" if _should_run(state, "gate_1_missing_spec") else "skip_missing_spec"

def gate_2_router(state: OrchestratorState) -> str:
    return "gate_2_sequencing" if _should_run(state, "gate_2_sequencing") else "skip_sequencing"

def gate_3_router(state: OrchestratorState) -> str:
    return "gate_3_option" if _should_run(state, "gate_3_option") else "skip_option"


def build_graph():
    graph = StateGraph(OrchestratorState)
    
    # 1. Initialization and Parallel Execution
    graph.add_node("orchestrator_init", orchestrator_init)
    graph.add_node("fetch_ds1", fetch_ds1)
    graph.add_node("fetch_ds2", fetch_ds2)
    graph.add_node("fetch_ds3", fetch_ds3)
    graph.add_node("fetch_ds4", fetch_ds4)
    graph.add_node("fetch_ds5", fetch_ds5)
    graph.add_node("join_all_sources", join_all_sources)
    
    # Gates and Nodes
    graph.add_node("gate_0_web_search", gate_0_web_search)
    graph.add_node("skip_web_search", skip_web_search)
    
    graph.add_node("gate_0b_world_knowledge", gate_0b_world_knowledge)
    graph.add_node("skip_world_knowledge", skip_world_knowledge)
    
    graph.add_node("gate_1_missing_spec", gate_1_missing_spec)
    graph.add_node("skip_missing_spec", skip_missing_spec)
    
    graph.add_node("gate_2_sequencing", gate_2_sequencing)
    graph.add_node("skip_sequencing", skip_sequencing)
    
    graph.add_node("gate_3_option", gate_3_option)
    graph.add_node("skip_option", skip_option)
    
    graph.add_node("gate_4_post_audit_verification", gate_4_post_audit_verification)
    
    graph.add_node("master_orchestrator", master_orchestrator_node)
    
    graph.add_node("output_assembly", output_assembly)
    
    graph.add_edge(START, "orchestrator_init")
    
    graph.add_edge("orchestrator_init", "fetch_ds1")
    graph.add_edge("orchestrator_init", "fetch_ds2")
    graph.add_edge("orchestrator_init", "fetch_ds3")
    graph.add_edge("orchestrator_init", "fetch_ds4")
    graph.add_edge("orchestrator_init", "fetch_ds5")
    
    graph.add_edge("fetch_ds1", "join_all_sources")
    graph.add_edge("fetch_ds2", "join_all_sources")
    graph.add_edge("fetch_ds3", "join_all_sources")
    graph.add_edge("fetch_ds4", "join_all_sources")
    graph.add_edge("fetch_ds5", "join_all_sources")
    
    graph.add_edge("join_all_sources", "master_orchestrator")
    
    # Gate 0 Routes
    graph.add_conditional_edges(
        "master_orchestrator",
        gate_0_router,
        {"gate_0_web_search": "gate_0_web_search", "skip_web_search": "skip_web_search"}
    )
    graph.add_conditional_edges("gate_0_web_search", gate_0b_router, {"gate_0b_world_knowledge": "gate_0b_world_knowledge", "skip_world_knowledge": "skip_world_knowledge"})
    graph.add_conditional_edges("skip_web_search", gate_0b_router, {"gate_0b_world_knowledge": "gate_0b_world_knowledge", "skip_world_knowledge": "skip_world_knowledge"})
    
    graph.add_conditional_edges("gate_0b_world_knowledge", gate_1_router, {"gate_1_missing_spec": "gate_1_missing_spec", "skip_missing_spec": "skip_missing_spec"})
    graph.add_conditional_edges("skip_world_knowledge", gate_1_router, {"gate_1_missing_spec": "gate_1_missing_spec", "skip_missing_spec": "skip_missing_spec"})
    
    graph.add_conditional_edges("gate_1_missing_spec", gate_2_router, {"gate_2_sequencing": "gate_2_sequencing", "skip_sequencing": "skip_sequencing"})
    graph.add_conditional_edges("skip_missing_spec", gate_2_router, {"gate_2_sequencing": "gate_2_sequencing", "skip_sequencing": "skip_sequencing"})
    
    graph.add_conditional_edges("gate_2_sequencing", gate_3_router, {"gate_3_option": "gate_3_option", "skip_option": "skip_option"})
    graph.add_conditional_edges("skip_sequencing", gate_3_router, {"gate_3_option": "gate_3_option", "skip_option": "skip_option"})
    
    # ROUTE TO VERIFICATION
    graph.add_edge("gate_3_option", "gate_4_post_audit_verification")
    graph.add_edge("skip_option", "gate_4_post_audit_verification")
    
    graph.add_edge("gate_4_post_audit_verification", "output_assembly")
    
    graph.add_edge("output_assembly", END)
    
    return graph.compile()
