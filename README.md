# Neo4j Graph Schema Toolkit for Claude

> A suite of Claude skills for designing Neo4j graph schemas, generating realistic test data, and loading it into a database — all from a single conversation.

[![Neo4j](https://img.shields.io/badge/Neo4j-5.x+-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Claude](https://img.shields.io/badge/Claude-Skills-D97706?logo=anthropic&logoColor=white)](https://claude.ai/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Models](https://img.shields.io/badge/Reference_Models-25-blue)](docs/models.md)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The Pipeline](#the-pipeline)
- [Available Reference Models](#available-reference-models)
- [Sample Workflows](#sample-workflows)
- [Skill Architecture](#skill-architecture)
- [Adding Custom Models](#adding-custom-models)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This toolkit provides an end-to-end pipeline for Neo4j graph database development:

```
Pick a reference model → Customize in visual editor → Generate test data → Load into Neo4j
```

**Key features:**

- **25 industry reference models** from [Neo4j's official use-case documentation](https://neo4j.com/developer/industry-use-cases/) covering Financial Services, Insurance, Healthcare, Manufacturing, and Cybersecurity
- **Interactive visual schema editor** — drag-and-drop nodes and relationships, edit properties, export as arrows.app JSON or Cypher
- **Context-aware data generation** — a `name` on a `Drug` node produces "Metformin", not "John Smith"
- **One-command Neo4j ingestion** — via MCP tools or a standalone Python script
- **arrows.app compatible** — export/import works with Neo4j's modeling tools

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Claude.ai account** | Pro, Team, or Enterprise plan with Skills enabled |
| **Python 3.9+** | For data generation and ingestion (runs inside Claude's sandbox) |
| **Neo4j instance** | Optional — only needed for Stage 6 (ingestion). [AuraDB Free](https://neo4j.com/cloud/aura-free/) works. |

### Optional: Neo4j MCP Connection

For direct database ingestion from Claude, connect the [Neo4j MCP tools](https://neo4j.com/labs/genai-ecosystem/neo4j-mcp/). Without it, you can still generate a standalone Python ingestion script.

---

## Installation

### Step 1: Download the Skills

Download all 5 `.skill` files from the [Releases](../../releases) page:

| File | Size | Purpose |
|---|---|---|
| `graph-schema-editor.skill` | ~12 KB | Interactive visual graph schema editor |
| `graph-reference-models.skill` | ~33 KB | 25 Neo4j industry reference data models |
| `graph-schema-from-reference.skill` | ~33 KB | Pipeline orchestrator + inject script |
| `graph-data-generator.skill` | ~15 KB | Context-aware fake data generation |
| `graph-neo4j-ingestion.skill` | ~6 KB | Database loading (MCP or Python script) |

### Step 2: Install in Claude

1. Open [Claude.ai](https://claude.ai)
2. Go to **Settings** → **Profile** → **Claude Skills**
3. Click **Add Skill** and upload each `.skill` file
4. Verify all 5 skills appear in your skills list

### Step 3: Verify Installation

Start a new conversation and say:

```
Show me the available Neo4j reference models
```

Claude should list all 25 models across 5 industries.

---

## Quick Start

### 30-Second Demo

Tell Claude:

```
Start from the insurance claims fraud model and generate 100 test records
```

Claude will:
1. Load the Claims Fraud schema (Claimant, Claim, MedicalProfessional, Vehicle) into the visual editor
2. Let you customize the schema (or just proceed)
3. Generate 100 claimants with realistic names, claims with proper IDs and amounts, doctors with "Dr." prefixed names, and vehicles with VIN numbers
4. Offer to load the data into Neo4j

### Your First Conversation

```
You: "I want to build a patient journey graph for healthcare analytics"

Claude: [Loads the schema editor with Patient, Encounter, Observation,
         Drug, Condition, Provider, Speciality, Organisation]

You: [Optional: customize the schema in the visual editor]
You: "Generate 1000 test records"

Claude: [Generates realistic healthcare data — drug names like "Metformin",
         conditions like "Type 2 Diabetes", providers like "Dr. Sarah Chen"]

You: "Give me the ingestion script"

Claude: [Provides a ready-to-run Python script]
```

---

## The Pipeline

The toolkit follows a 6-stage pipeline. You can stop at any stage.

```
┌─────────┐    ┌─────────────┐    ┌────────────┐
│ Stage 1  │    │   Stage 2   │    │  Stage 3   │
│  Pick    │───>│   Schema    │───>│ Customize  │
│  Model   │    │   Editor    │    │ (optional) │
└─────────┘    └─────────────┘    └────────────┘
                                        │
                                        v
┌─────────┐    ┌─────────────┐    ┌────────────┐
│ Stage 6  │    │   Stage 5   │    │  Stage 4   │
│  Ingest  │<───│  Generate   │<───│  Export    │
│  Neo4j   │    │   Data      │    │  Schema    │
└─────────┘    └─────────────┘    └────────────┘
```

### Stage 1 — Pick a Reference Model

Tell Claude what domain you're working in. It matches your request to one of 25 models.

### Stage 2 — Schema Editor (Auto-loaded)

An interactive visual editor appears as an artifact with your chosen reference model pre-loaded.

**Editor Features:**
- Pan & zoom (scroll wheel + drag)
- Add nodes (double-click canvas)
- Create relationships (drag from node edge to another node)
- Edit properties (click any element → sidebar)
- Self-loops (drag from node back to itself)
- Import/Export (arrows.app JSON + Cypher)

### Stage 3 — Customize (Optional)

Add, remove, or edit nodes, relationships, and properties to match your exact needs.

### Stage 4 — Export Schema

Click **Export** → **Copy JSON** → Paste into chat. Or simply tell Claude "looks good, generate data".

### Stage 5 — Generate Test Data

Claude generates realistic, context-aware fake data as CSV files. You choose the scale:

| Scale | Records | Best For |
|---|---|---|
| Small | ~100 | Quick testing, demos |
| Medium | ~1,000 | Development (default) |
| Large | ~10,000 | Load testing, performance |
| Custom | You specify | Specific requirements |

**Context-aware generation** — the generator knows what kind of data each node expects:

| Node Label | Property | Generated Value |
|---|---|---|
| `Drug` | `name` | "Metformin", "Aspirin", "Lisinopril" |
| `Condition` | `description` | "Type 2 Diabetes Mellitus", "Essential Hypertension" |
| `MedicalProfessional` | `name` | "Dr. Sarah Chen", "Dr. James Wilson" |
| `Vehicle` | `VIN` | "J5242AH7E86SJICXL" |
| `ComputeInstance` | `hostname` | "web-prod-03.internal" |
| `CVE` | `cveId` | "CVE-2024-31205" |
| `Gene` | `symbol` | "TP53", "BRCA1", "EGFR" |
| `Patent` | `title` | "Selective inhibitor of BACE1" |

### Stage 6 — Load into Neo4j

**Option A: Direct MCP** (if Neo4j tools connected) — Claude runs Cypher directly.

**Option B: Python Script** — Claude provides `ingest_data.py`:

```bash
python ingest_data.py ./graph_data \
    --uri bolt://localhost:7687 \
    --user neo4j \
    --password <your-password>
```

---

## Available Reference Models

### Financial Services (11 models)

| Model ID | Name | Nodes | Rels | Source |
|---|---|:---:|:---:|---|
| `transaction-base-model` | Transaction & Account Base Model | 19 | 24 | [Link](https://neo4j.com/developer/industry-use-cases/data-models/transaction-graph/transaction/transaction-base-model/) |
| `fraud-event-sequence` | Fraud Event Sequence Model | 13 | 26 | [Link](https://neo4j.com/developer/industry-use-cases/data-models/transaction-graph/fraud-event-sequence/fraud-event-sequence-model/) |
| `regulatory-dependency-mapping` | Regulatory Dependency Mapping | 2 | 3 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/investment-banking/regulatory-dependency-mapping/) |
| `mutual-fund-dependency` | Mutual Fund Dependency Analytics | 3 | 2 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/investment-banking/mutual-fund-dependency/) |
| `deposit-analysis` | Deposit Analysis | 3 | 3 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/deposit-analysis/) |
| `account-takeover-fraud` | Account Takeover Fraud | 9 | 9 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/account-takeover-fraud/) |
| `automated-facial-recognition` | Automated Facial Recognition | 1 | 0 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/automated-facial-recognition/) |
| `synthetic-identity-fraud` | Synthetic Identity Fraud | 4 | 4 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/synthetic-identity-fraud/) |
| `transaction-fraud-ring` | Transaction Fraud Ring | 2 | 2 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/transaction-ring/) |
| `transaction-monitoring` | Transaction Monitoring | 7 | 7 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/transaction-monitoring/transaction-monitoring-introduction/) |
| `transaction-fraud-detection` | Transaction Fraud Detection (IEEE-CIS) | 6 | 5 | [Link](https://neo4j.com/developer/industry-use-cases/finserv/retail-banking/ieee-cis-fraud-graphs/) |

### Insurance (2 models)

| Model ID | Name | Nodes | Rels | Source |
|---|---|:---:|:---:|---|
| `claims-fraud` | Insurance Claims Fraud | 4 | 5 | [Link](https://neo4j.com/developer/industry-use-cases/insurance/claims-fraud/) |
| `quote-fraud` | Insurance Quote Fraud | 1 | 1 | [Link](https://neo4j.com/developer/industry-use-cases/insurance/quote-fraud/) |

### Healthcare & Life Sciences (5 models)

| Model ID | Name | Nodes | Rels | Source |
|---|---|:---:|:---:|---|
| `patient-journey` | Patient Journey | 8 | 8 | [Link](https://neo4j.com/developer/industry-use-cases/life-sciences/medical-care/patient-journey/) |
| `patent-intelligence` | Patent Intelligence | 6 | 6 | [Link](https://neo4j.com/developer/industry-use-cases/life-sciences/competitive-intelligence/patent-intelligence/) |
| `publication-intelligence` | Publication Intelligence | 5 | 5 | [Link](https://neo4j.com/developer/industry-use-cases/life-sciences/competitive-intelligence/publication-intelligence/) |
| `single-omics` | Single-omics Data Integration | 6 | 7 | [Link](https://neo4j.com/developer/industry-use-cases/life-sciences/research-development/single-omics/) |
| `multi-omics` | Multi-omics Data Integration | 8 | 9 | [Link](https://neo4j.com/developer/industry-use-cases/life-sciences/research-development/multi-omics/) |

### Manufacturing (4 models)

| Model ID | Name | Nodes | Rels | Source |
|---|---|:---:|:---:|---|
| `ev-route-planning` | Electric Vehicle Route Planning | 3 | 3 | [Link](https://neo4j.com/developer/industry-use-cases/manufacturing/supply-chain-management/ev-route-planning/) |
| `configurable-bom` | Configurable Bill of Materials | 4 | 4 | [Link](https://neo4j.com/developer/industry-use-cases/manufacturing/product-design-and-engineering/configurable-bom/) |
| `engineering-traceability` | Engineering Traceability | 4 | 4 | [Link](https://neo4j.com/developer/industry-use-cases/manufacturing/product-design-and-engineering/engineering-traceability/) |
| `process-monitoring-cpa` | Process Monitoring & CPA | 3 | 6 | [Link](https://neo4j.com/developer/industry-use-cases/manufacturing/production-planning-and-optimization/process-monitoring-and-cpa/) |

### Cybersecurity (3 models)

| Model ID | Name | Nodes | Rels | Source |
|---|---|:---:|:---:|---|
| `vulnerability-prioritization` | Vulnerability Prioritization (VPEM) | 7 | 6 | [Link](https://neo4j.com/developer/industry-use-cases/cybersecurity/vulnerability-prioritization-exposure-management/) |
| `attack-path-analysis` | Attack Path Analysis | 6 | 6 | [Link](https://neo4j.com/developer/industry-use-cases/cybersecurity/attack-path-analysis/) |
| `software-supply-chain-security` | Software Supply Chain (SBOM) | 5 | 5 | [Link](https://neo4j.com/developer/industry-use-cases/cybersecurity/software-supply-chain-security/) |

---

## Sample Workflows

### Workflow 1: Insurance Fraud Investigation Demo

```
You:    "Start from the insurance claims fraud model"
Claude: [Loads editor with Claimant, Claim, MedicalProfessional, Vehicle]

You:    [Adds a Policy node, adds HAS_POLICY relationship]
You:    "Generate 1000 records"
Claude: [Generates CSVs with realistic insurance data]

You:    "Load it into my Neo4j database"
Claude: [Runs ingestion via MCP or provides script]
```

### Workflow 2: Patient Journey Analytics

```
You:    "I need a patient journey model for a hospital system"
Claude: [Loads Patient, Encounter, Observation, Drug, Condition,
         Provider, Speciality, Organisation + NEXT chain]

You:    "Add a CareTeam node connected to Encounter"
You:    [Exports JSON and pastes it]

You:    "Generate a large dataset — 10,000 patients"
Claude: [Generates data with real drug names, ICD codes, specialties]
```

### Workflow 3: Cybersecurity Attack Path Analysis

```
You:    "Load the attack path analysis model"
Claude: [Loads ComputeInstance, Application, CVE, Identity,
         IAMPolicy, CrownJewel + CAN_REACH]

You:    "Looks good. Generate medium-scale data."
Claude: [Generates realistic hostnames, CVE IDs, IAM policies]

You:    "Give me Cypher to find paths to crown jewels"
Claude: [Writes the path-finding query]
```

### Workflow 4: Quick Schema Exploration

```
You:    "Show me the transaction base model"
Claude: [Loads the full 19-node banking schema]

You:    [Explores schema, clicks Export → Cypher tab → Copy]
You:    [Pastes Cypher directly into Neo4j Browser]
```

### Workflow 5: Custom Schema (No Reference Model)

```
You:    "Design a graph schema for a movie recommendation system"
Claude: [Creates a custom schema from scratch using the editor]
        [No reference model needed — direct schema design]
```

---

## Skill Architecture

```
neo4j-graph-schema-toolkit/
│
├── README.md
├── LICENSE
│
├── skills/
│   ├── graph-schema-editor.skill
│   ├── graph-reference-models.skill
│   ├── graph-schema-from-reference.skill
│   ├── graph-data-generator.skill
│   └── graph-neo4j-ingestion.skill
│
└── src/
    ├── graph-schema-editor/
    │   ├── SKILL.md
    │   └── assets/
    │       └── graph-editor-template.jsx     # Self-contained React component
    │
    ├── graph-reference-models/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── inject_model.py               # Injects model into editor template
    │   └── references/
    │       ├── model-index.json              # Catalog of all 25 models
    │       ├── transaction-base-model.json
    │       ├── claims-fraud.json
    │       ├── patient-journey.json
    │       └── ... (25 JSON files)
    │
    ├── graph-schema-from-reference/
    │   ├── SKILL.md                          # Pipeline orchestrator (Stages 1-6)
    │   ├── scripts/
    │   │   └── inject_model.py
    │   └── references/
    │       └── ... (25 JSON files)
    │
    ├── graph-data-generator/
    │   ├── SKILL.md
    │   └── assets/
    │       └── generate_data.py              # Context-aware Faker generator
    │
    └── graph-neo4j-ingestion/
        ├── SKILL.md
        └── assets/
            └── ingest_data.py                # Neo4j Python driver loader
```

---

## Adding Custom Models

You can add your own reference models by creating a JSON file:

```json
{
  "id": "my-custom-model",
  "name": "My Custom Model",
  "description": "Description of the model. Source: https://...",
  "industry": "My Industry",
  "tags": ["tag1", "tag2"],
  "initialGraph": {
    "nodes": [
      {
        "id": "n0",
        "position": { "x": 400, "y": 200 },
        "caption": "MyNode",
        "labels": ["MyNode"],
        "properties": { "id": "string", "name": "string" },
        "style": { "color": "#4C8BF5", "radius": 50 }
      }
    ],
    "relationships": [
      {
        "id": "r0",
        "type": "RELATES_TO",
        "fromId": "n0",
        "toId": "n0",
        "properties": {}
      }
    ],
    "style": {}
  }
}
```

Place it in the `references/` folder and update `model-index.json`.

To add context-aware data generation for your custom nodes, add entries to `CONTEXT_GENERATORS` in `generate_data.py`:

```python
CONTEXT_GENERATORS = {
    # ...existing entries...
    ("mynode", "name"): lambda: random.choice(["Value1", "Value2", "Value3"]),
    ("mynode", "status"): lambda: random.choice(["active", "inactive"]),
}
```

---

## Troubleshooting

### Export Copy Button Doesn't Work

The editor uses `document.execCommand('copy')` which works in Claude's artifact sandbox. If it fails, click the code preview area to select all text, then use <kbd>Ctrl</kbd>+<kbd>C</kbd> / <kbd>Cmd</kbd>+<kbd>C</kbd> manually.

### Claude Asks for Schema After "Generate Data"

If you customized the schema, you need to export the JSON and paste it into the chat. If you didn't change anything, say "use the reference model as-is" or "looks good, generate data".

### Package Installation Fails

The data generator uses a Python virtual environment. If `faker` or `neo4j` fails to install, check that `pypi.org` and `files.pythonhosted.org` are in Claude's allowed network domains.

### Neo4j Connection Refused

- Ensure your Neo4j instance is running
- For AuraDB: use `neo4j+s://` protocol
- For local: use `bolt://localhost:7687`
- Check credentials (username/password)

### Generated Data Is Out of Context

The data generator uses context-aware generation based on node labels. If you're seeing generic data, ensure your node labels match common patterns (e.g., `Drug`, `Patient`, `Vehicle`). You can also add custom generators — see [Adding Custom Models](#adding-custom-models).

---

## Contributing

Contributions welcome! Some areas where help is appreciated:

- **New reference models** — add models for industries not yet covered
- **Context generators** — improve data realism for specific domains
- **Schema editor features** — UI improvements, new export formats
- **Documentation** — tutorials, video walkthroughs

Please open an issue before submitting a PR for major changes.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Reference data models are based on schemas from [Neo4j's industry use-case documentation](https://neo4j.com/developer/industry-use-cases/) and are used in accordance with Neo4j's developer documentation terms.

---

## Acknowledgments

- **Neo4j** — for the [industry use-case documentation](https://neo4j.com/developer/industry-use-cases/) that the reference models are sourced from
- **arrows.app** — for the JSON schema format used throughout the toolkit
- **Faker** — for the Python library powering realistic data generation
