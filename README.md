# Neo4j Graph Schema Toolkit for Claude

> A suite of Claude skills for designing Neo4j graph schemas, generating realistic test data, and loading it into a database — all from a single conversation.

[![Neo4j](https://img.shields.io/badge/Neo4j-5.x+-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Claude](https://img.shields.io/badge/Claude-Skills-D97706?logo=anthropic&logoColor=white)](https://claude.ai/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Models](https://img.shields.io/badge/Reference_Models-25-blue)](#available-reference-models)
[![SE Skills](https://img.shields.io/badge/SE_Skills-3-purple)](#se-skills-for-solutions-engineers)

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The Pipeline](#the-pipeline)
- [Available Reference Models](#available-reference-models)
- [Sample Workflows](#sample-workflows)
- [SE Skills for Solutions Engineers](#se-skills-for-solutions-engineers)
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
- **3 SE workflow skills** — use-case discovery workshop, business case / ROI snapshot, and POC plan, each producing a slide-ready HTML artifact for customer conversations
- **Interactive visual schema editor** — drag-and-drop nodes and relationships, edit properties, export as arrows.app JSON or Cypher
- **Context-aware data generation** — a `name` on a `Drug` node produces "Metformin", not "John Smith"
- **One-command Neo4j ingestion** — via MCP tools or a standalone Python script
- **arrows.app compatible** — export/import works with Neo4j's modeling tools

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Claude.ai or Claude Desktop** | Pro, Team, or Enterprise plan with Skills enabled. Works on both [claude.ai](https://claude.ai) and the [Claude Desktop app](https://claude.ai/download). |
| **Python 3.9+** | For data generation and ingestion (runs inside Claude's sandbox) |
| **Neo4j instance** | Optional — only needed for Stage 6 (ingestion). [AuraDB Free](https://neo4j.com/cloud/aura-free/) works. |

### Optional: Neo4j MCP Connection

For direct database ingestion from Claude, connect the [Neo4j MCP tools](https://neo4j.com/labs/genai-ecosystem/neo4j-mcp/). Without it, you can still generate a standalone Python ingestion script.

---

## Installation

### Step 1: Download the Skills

Download all 5 `.skill` files from the [`skills/`](skills/) directory:

**Graph schema pipeline:**

| File | Purpose |
|---|---|
| `graph-schema-studio.skill` | Interactive visual editor + 25 industry reference models |
| `graph-data-workflow.skill` | 6-step conversational flow for generating synthetic data |

**SE workflow:**

| File | Purpose |
|---|---|
| `se-workshop.skill` | Progressive use-case discovery board (column-by-column facilitation) |
| `se-value-case.skill` | Business case + ROI snapshot artifact |
| `se-poc-doc.skill` | POC plan + executive summary artifact |

### Step 2: Install in Claude

The skills work on both **Claude.ai (web)** and the **Claude Desktop app**.

**Claude.ai (Web):**
1. Open [claude.ai](https://claude.ai)
2. Go to **Settings** → **Profile** → **Claude Skills**
3. Click **Add Skill** and upload each `.skill` file

**Claude Desktop App:**
1. Open the [Claude Desktop app](https://claude.ai/download)
2. Go to **Settings** → **Customize** → **Claude Skills**
3. Click **Add Skill** and upload each `.skill` file

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

### Stage 4 — Export Your Schema

When you're happy with the schema:

1. Click the **Export** button in the editor
2. Select the **Arrows JSON** tab
3. Click **Copy JSON** (copies to your clipboard)
4. **Paste it into the chat**

> **Tip:** If you didn't change anything from the reference model, you can simply tell Claude *"looks good, generate data"* — it will use the reference model schema directly without needing a paste.

### Stage 5 — Generate Test Data

Claude generates realistic, context-aware fake data as CSV files:

| Scale | Records | Best For |
|---|---|---|
| Small | ~100 | Quick testing, demos |
| Medium | ~1,000 | Development (default) |
| Large | ~10,000 | Load testing, performance |
| Custom | You specify | Specific requirements |

**Context-aware generation examples:**

| Node Label | Property | Generated Value |
|---|---|---|
| `Drug` | `name` | "Metformin", "Aspirin", "Lisinopril" |
| `Condition` | `description` | "Type 2 Diabetes Mellitus", "Essential Hypertension" |
| `MedicalProfessional` | `name` | "Dr. Sarah Chen", "Dr. James Wilson" |
| `Vehicle` | `VIN` | "J5242AH7E86SJICXL" |
| `ComputeInstance` | `hostname` | "web-prod-03.internal" |
| `CVE` | `cveId` | "CVE-2024-31205" |
| `Gene` | `symbol` | "TP53", "BRCA1", "EGFR" |
| `Machine` | `name` | "AssemblyMachine7" |

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

You:    [Adds a Policy node, customizes properties]
You:    "Generate 1000 records"
Claude: [Generates CSVs with proper claim IDs, "Dr." prefixed names, VINs]

You:    "Load it into my Neo4j database"
Claude: [Runs ingestion via MCP or provides script]
```

### Workflow 2: Patient Journey Analytics

```
You:    "I need a patient journey model for a hospital system"
Claude: [Loads Patient, Encounter, Observation, Drug, Condition,
         Provider, Speciality, Organisation + NEXT chain]

You:    "Add a CareTeam node connected to Encounter via ASSIGNED_TO"
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

You:    [Clicks Export → Cypher tab → Copy]
You:    [Pastes Cypher directly into Neo4j Browser]
```

### Workflow 5: Custom Schema from Scratch

```
You:    "Design a graph schema for a movie recommendation system"
Claude: [Creates a custom schema from scratch using the editor]
```

---

## SE Skills for Solutions Engineers

Three skills designed for SE/AE customer conversations. They work independently or chained together — workshop output feeds naturally into the value case, which feeds into the POC doc.

```
se-workshop  →  se-value-case  →  se-poc-doc
(discovery)     (business case)   (POC plan)
```

### `se-workshop` — Use Case Value Workshop

A progressive discovery board built column-by-column. Claude acts as a senior SE + Challenger, asking one column at a time and pushing back on vague answers.

**Trigger phrases:** "workshop", "value workshop", "use case workshop", "discovery session", "prepare for customer", "ROI for Neo4j", "help me build the business case"

**What it produces:** A rendered HTML board with 6 columns — Business Scope, Current Business Landscape, Current Technical Landscape, Technical Scope, Stakeholders, and Success Metrics. Gaps become orange cards with specific facilitation questions to ask the customer.

**Two modes:**
- **Prep** — solo, up to 2 follow-up questions per column, Challenger pushes on vague answers
- **Live** — customer present, one question per column, render immediately

```
You: "Let's run a workshop for a fraud detection use case at a tier-1 bank"

Claude: [Asks mode: Prep or Live]
You:    "Prep"
Claude: [Asks about business scope — checkbox with 4–6 options]
You:    [Selects answers]
Claude: [Renders column 1, gives one Challenger insight, moves to column 2]
...
Claude: [Completes all 6 columns + inline facilitation guide]
```

---

### `se-value-case` — Business Case & ROI

Reads from the current conversation (se-workshop output or direct input). Asks only for what is genuinely missing — never invents numbers.

**Trigger phrases:** "business case", "ROI", "value narrative", "value case", "cost of inaction", "quantify the value", "build the business case", "what's the ROI"

**What it produces:** A single-page dark-theme HTML artifact with two sections:
1. **Business Case** — executive narrative, problem statement, cost of inaction, value drivers, quantified impact (ranges if data exists)
2. **ROI Snapshot** — four metric tiles (time saved, cost avoided, revenue impact, risk reduction)

All numbers are labelled as estimates. Gaps are marked `[ ? ]` with a note on what to ask the customer.

```
You: "Build the business case based on what we just covered"

Claude: [Reads workshop output, asks at most 3 targeted questions for missing numbers]
You:    [Provides baseline metrics]
Claude: [Renders single-page HTML artifact — slide-ready]
```

---

### `se-poc-doc` — POC Plan & Executive Summary

Reads from the current conversation. Produces a two-section HTML artifact: a structured POC plan and a slide-ready one-pager executive summary. Designed to prove a buying decision, not technology.

**Trigger phrases:** "POC", "PoC plan", "proof of concept", "exec summary", "executive summary", "POV plan", "proof of value", "next steps document", "send to customer", "build the POC"

**What it produces:** A single-page HTML artifact with two sections:
1. **POC Plan** — objective, hypotheses, scope, data required, success criteria (binary, flagged if vague), timeline, customer commitments, exit criteria
2. **Executive Summary** — C-level one-pager designed to be screenshot directly into a slide deck

```
You: "Now build the POC doc"

Claude: [Reads conversation for buying decision + success criteria, asks at most 2 questions]
You:    [Answers]
Claude: [Renders POC plan + exec summary in one artifact]
```

---

### Chained Workflow Example

```
You:    "Let's run a workshop for a supply chain risk use case"
Claude: [se-workshop: 6-column discovery board]

You:    "Build the business case from this"
Claude: [se-value-case: business case + ROI artifact]

You:    "Now write up the POC plan"
Claude: [se-poc-doc: POC plan + exec summary artifact]
```

---

## Skill Architecture

```
neo4j-graph-schema-toolkit/
│
├── README.md
├── LICENSE
│
├── skills/                              ← deployable .skill files (ZIP)
│   ├── graph-schema-studio.skill        ← Visual editor + 25 reference models
│   ├── graph-data-workflow.skill        ← 6-step synthetic data generation
│   ├── se-workshop.skill                ← Use case discovery board
│   ├── se-value-case.skill              ← Business case + ROI artifact
│   └── se-poc-doc.skill                 ← POC plan + exec summary artifact
│
└── src/
    ├── graph-data-workflow/
    │   ├── SKILL.md
    │   ├── assets/                      ← Faker generator scripts
    │   └── scripts/
    │
    ├── graph-data-generator/
    │   ├── SKILL.md
    │   └── assets/generate_data.py
    │
    ├── se-workshop/
    │   └── SKILL.md                     ← Discovery board + facilitation rules
    │
    ├── se-value-case/
    │   └── SKILL.md                     ← Business case + ROI generation rules
    │
    └── se-poc-doc/
        └── SKILL.md                     ← POC plan + exec summary rules
```

---

## Adding Custom Models

Create a JSON file following the arrows.app format:

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

To add context-aware data generation, add entries to `CONTEXT_GENERATORS` in `generate_data.py`:

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

If you customized the schema, you need to export the JSON and paste it into the chat. If you didn't change anything, say *"use the reference model as-is"*.

### Package Installation Fails

The data generator uses a Python virtual environment. If `faker` or `neo4j` fails to install, check that `pypi.org` and `files.pythonhosted.org` are in Claude's allowed network domains.

### Neo4j Connection Refused

Ensure your Neo4j instance is running and the URI/credentials are correct. For AuraDB, use `neo4j+s://` protocol. For local instances, use `bolt://localhost:7687`.

### Generated Data Is Out of Context

Ensure your node labels match common patterns (e.g., `Drug`, `Patient`, `Vehicle`). You can add custom generators — see [Adding Custom Models](#adding-custom-models).

---

## Contributing

Contributions welcome! Areas where help is appreciated:

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

- **[Neo4j](https://neo4j.com/)** — for the [industry use-case documentation](https://neo4j.com/developer/industry-use-cases/) that the reference models are sourced from
- **[arrows.app](https://arrows.app/)** — for the JSON schema format used throughout the toolkit
- **[Faker](https://faker.readthedocs.io/)** — for the Python library powering realistic data generation
