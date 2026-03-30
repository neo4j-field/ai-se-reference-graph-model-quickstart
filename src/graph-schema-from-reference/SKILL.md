---
name: graph-schema-from-reference
description: >
  Instantly launch the interactive graph schema editor pre-loaded with a Neo4j reference
  data model. Bridges the graph-reference-models and graph-schema-editor skills. Trigger
  whenever a user wants to visualize, explore, edit, or start from any Neo4j industry
  reference model — including "show me the claims fraud model", "open the transaction model
  in the editor", "load the patient journey schema", "visualize the attack path model",
  "start from the BOM reference", "edit the SBOM graph model", or any combination of a
  reference model name with words like "editor", "visualize", "open", "load", "show",
  "explore", "start from", "edit", "customize". Also trigger when the user picks a model
  from the graph-reference-models catalog and wants to see it visually. This is the glue
  skill — it automates the entire pipeline from model selection to interactive editor.
---

# Graph Schema from Reference — Full Pipeline

End-to-end orchestrator that takes a user from picking a Neo4j reference model all the way
through to data generation and Neo4j ingestion. The pipeline has 6 stages:

```
 1. Pick reference model
 2. Inject into schema editor    ← automatic (inject_model.py)
 3. User customizes in editor    ← interactive (user exports JSON when done)
 4. User signals "done"          ← wait for user
 5. Generate fake data           ← graph-data-generator skill
 6. Create ingestion script      ← graph-neo4j-ingestion skill
```

## Stage 1 → Pick Reference Model

If the user named a specific model, map it to a model ID using the table below.
If unclear, list available models:

```bash
python3 scripts/inject_model.py --list
```

**Model ID Quick Reference:**

| Keyword | Model ID |
|---------|----------|
| banking, transactions, KYC | `transaction-base-model` |
| fraud event sequence | `fraud-event-sequence` |
| regulatory, compliance | `regulatory-dependency-mapping` |
| mutual fund, investment | `mutual-fund-dependency` |
| deposit | `deposit-analysis` |
| account takeover, ATO | `account-takeover-fraud` |
| facial recognition, biometric | `automated-facial-recognition` |
| synthetic identity | `synthetic-identity-fraud` |
| fraud ring, circular | `transaction-fraud-ring` |
| transaction monitoring, AML | `transaction-monitoring` |
| IEEE-CIS, fraud detection ML | `transaction-fraud-detection` |
| insurance claims | `claims-fraud` |
| insurance quote, ghost broker | `quote-fraud` |
| patient journey, healthcare | `patient-journey` |
| patent, IP | `patent-intelligence` |
| publication, KOL | `publication-intelligence` |
| single-omics, genomics | `single-omics` |
| multi-omics | `multi-omics` |
| EV, route planning | `ev-route-planning` |
| BOM, bill of materials | `configurable-bom` |
| traceability | `engineering-traceability` |
| process monitoring, critical path | `process-monitoring-cpa` |
| vulnerability, CVE | `vulnerability-prioritization` |
| attack path, lateral movement | `attack-path-analysis` |
| SBOM, software supply chain | `software-supply-chain-security` |

## Stage 2 → Inject into Schema Editor

Run:

```bash
python3 scripts/inject_model.py <model-id>
```

This auto-detects the graph-editor-template.jsx from the graph-schema-editor skill,
injects the reference model's initialGraph, and writes to
`/mnt/user-data/outputs/graph-schema-editor.jsx`.

Present the file and tell the user:
- The editor is pre-loaded with **{model name}** ({node count} nodes, {rel count} relationships)
- Source: {URL from the model JSON}
- They can add/remove nodes, edit properties, create/delete relationships
- Double-click canvas to add nodes; drag from node edge to create relationships
- **When they're happy with the schema, click Export → arrows.app JSON and paste it back**

## Stage 3 → User Customizes

Wait for the user. They will interact with the schema editor artifact and may:
- Add or remove nodes
- Edit property names and types
- Create or delete relationships
- Rename labels

When they're done, they'll either:
- Paste the exported arrows.app JSON back into the chat
- Say something like "done", "looks good", "generate data", "next step"
- Ask to proceed with data generation

## Stage 4 → Capture the Final Schema

When the user signals they're done:

**If they pasted JSON:** Save it directly:
```bash
# Save the user's exported JSON to the working file
cat > /home/claude/graph_schema.json << 'SCHEMA'
{paste the user's JSON here}
SCHEMA
```

**If they said "done" without pasting:** The reference model's own schema is the fallback.
Convert the reference model JSON to the arrows.app format the data generator expects:

```bash
python3 -c "
import json
with open('path/to/reference-model.json') as f:
    model = json.load(f)
output = {'graph': model['initialGraph']}
with open('/home/claude/graph_schema.json', 'w') as f:
    json.dump(output, f, indent=2)
print('Schema saved to /home/claude/graph_schema.json')
"
```

## Stage 5 → Generate Fake Data

Now use the **graph-data-generator** skill. Read its SKILL.md for full details, but the
key steps are:

```bash
# Ensure venv exists
if [ ! -d "/home/claude/graph_venv" ]; then
    python3 -m venv /home/claude/graph_venv
fi
/home/claude/graph_venv/bin/pip install faker -q

# Copy the generator script
cp /mnt/skills/user/graph-data-generator/assets/generate_data.py /home/claude/generate_data.py

# Run it (ask user for scale: 100/1000/10000 — default 1000)
/home/claude/graph_venv/bin/python3 /home/claude/generate_data.py \
  /home/claude/graph_schema.json \
  --output-dir /home/claude/graph_data \
  --scale <SCALE>
```

Present the generated CSVs and manifest from `/home/claude/graph_data/` to the user.

## Stage 6 → Create Ingestion Script

Use the **graph-neo4j-ingestion** skill. Read its SKILL.md for full details, but the
key steps are:

**Option A — Direct MCP ingestion** (if Neo4j MCP tools are connected):
Follow the graph-neo4j-ingestion Mode A instructions to UNWIND-load the CSVs directly.

**Option B — Standalone script** (default):
```bash
# Install neo4j driver
/home/claude/graph_venv/bin/pip install neo4j -q

# Copy the ingestion script
cp /mnt/skills/user/graph-neo4j-ingestion/assets/ingest_data.py /home/claude/ingest_data.py
cp /home/claude/ingest_data.py /mnt/user-data/outputs/ingest_data.py
```

Present the ingestion script and tell the user how to run it:
```bash
python ingest_data.py ./graph_data \
    --uri bolt://localhost:7687 \
    --user neo4j \
    --password <your-password>
```

## Putting It All Together — Example Conversation Flow

```
User: "I want to start from the insurance claims fraud model"

Claude: [Stage 1] Identifies → claims-fraud
        [Stage 2] Runs inject_model.py claims-fraud
        [Stage 2] Presents the schema editor artifact
        [Stage 2] "Here's the Claims Fraud reference model loaded in the editor.
                   It has 4 nodes (Claimant, Claim, MedicalProfessional, Vehicle)
                   and 5 relationships. Customize it as needed — when you're done,
                   export the JSON or let me know and I'll proceed to data generation."

User: *adds a Policy node, edits some properties*
User: "Looks good, generate some test data"

Claude: [Stage 4] If user pasted JSON, saves it. Otherwise uses reference model.
        [Stage 5] Asks for scale (default 1000), runs generate_data.py
        [Stage 5] "Generated 1000 Claimants, 2500 Claims, 50 MedicalProfessionals,
                   800 Vehicles. Here are the CSV files."

User: "Now load it into Neo4j" or "Give me the ingestion script"

Claude: [Stage 6] Runs ingestion via MCP or presents the standalone script
```

## Dependencies

This skill orchestrates three other skills:
- **graph-schema-editor** — provides the JSX template
- **graph-reference-models** — provides reference model JSONs (also bundled in this skill)
- **graph-data-generator** — provides generate_data.py
- **graph-neo4j-ingestion** — provides ingest_data.py

## Error Handling

- If graph-schema-editor is not installed → inject_model.py prints an error about
  missing template. Tell the user they need the skill installed.
- If the user's exported JSON is malformed → validate it has `graph.nodes` and
  `graph.relationships` keys before passing to the data generator.
- If faker fails to install → check network connectivity and suggest manual install.
