# Industrial Category Spec Intelligence - Multi-Agent Pipeline

Bhai, ye hamara complete pipeline hai for Industrial Spec Discovery, Sequencing, and Option Audit. 

## 🚀 How to Setup (For your friend)

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/Manan0802/multi-agent.git
   cd multi-agent
   ```

2. **Create Virtual Environment** (Recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set API Keys**:
   Make sure to set your LLM Gateway API Key in your environment or update `orchestrator/nodes.py`.
   ```bash
   export LLM_GATEWAY_API_KEY="your-key-here"
   ```

## 🏗️ Project Structure
- `orchestrator/`: Core logic nodes and graph builder.
- `data_loader.py`: Specialized fetchers for DS0, DS1, DS2, DS3, DS4, DS5 (CSVs and APIs).
- `master_orchestrator_node.py`: The streaming "Brain" with reinforced thinking layer.
- `Blueprints/`: JSON files for n8n integration.

## 🏃 How to Run
Run the main orchestrator script directly:
```bash
python orchestrator/main.py
```

Bhai, logic ab bilkul industrial standards par hai with full traces logged. Enjoy coding! ✅🏁⚒️📊🦾
