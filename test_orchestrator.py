import os
import sys

# Ensure the root directory is accessible for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from orchestrator.main import run_orchestrator

# Set the API Key
os.environ["LLM_GATEWAY_API_KEY"] = "sk--JySdoIyO60SH5UixKsZSQ"

mcat_id = "3983"
category_name = "conference tables"

print(f"Testing with MCAT: {mcat_id}, Category: {category_name}")
try:
    final_state = run_orchestrator(mcat_id, category_name)
    print("\n--- TEST COMPLETED ---")
    output = final_state.get('final_output', {})
    print(f"Summary: {output.get('Summary')}")
    if "Master_Decision" in output:
        print(f"Confidence: {output.get('Master_Decision', {}).get('confidence')}")
        print(f"Anomalies: {output.get('Master_Decision', {}).get('anomalies')}")
except Exception as e:
    import traceback
    print(f"Test failed: {str(e)}")
    traceback.print_exc()
