---
name: graph-reference-models
description: >
  Load Neo4j reference data models as starting points for the graph-schema-editor. 25 models
  across Financial Services, Insurance, Healthcare, Manufacturing, and Cybersecurity from
  neo4j.com/developer/industry-use-cases. Trigger when users ask for a "reference model",
  "Neo4j data model", "industry template", or pre-built graph schema for banking, fraud,
  insurance claims, patient journey, supply chain, BOM, omics, patent intelligence, attack
  path, SBOM, or any Neo4j use case. Also trigger for "start from the transaction model",
  "load the fraud model", "banking data model", "configurable BOM model", "vulnerability
  graph". Provides initialGraph objects for the graph-schema-editor template. Do NOT use for
  designing schemas from scratch (use graph-schema-editor) or generating fake data (use
  graph-data-generator).
---

# Graph Reference Models

Pre-built Neo4j data models sourced from Neo4j's official industry use-case documentation.
These models serve as production-quality starting points for the graph-schema-editor, giving
users a head start with battle-tested schemas instead of building from scratch.

## When to Use

- User wants to start from an established Neo4j data model pattern
- User is working in financial services, insurance, healthcare, manufacturing, or cybersecurity
- User references Neo4j's industry use-case documentation
- User asks for a "reference model", "template schema", or "industry standard" graph model
- User wants to extend or customize an existing Neo4j reference model

## Quick Start — Loading a Reference Model into the Schema Editor

This is the primary workflow. It takes one command to go from a reference model to a live,
interactive schema editor.

### Step 1: Pick the model

Identify which reference model to use (see catalog below). If the user doesn't specify,
show them the options or match based on their domain keywords.

### Step 2: Run the inject script

```bash
python3 /path/to/graph-reference-models/scripts/inject_model.py \
  /path/to/graph-reference-models/references/<model-id>.json \
  /mnt/skills/user/graph-schema-editor/assets/graph-editor-template.jsx \
  /mnt/user-data/outputs/graph-schema-editor.jsx
```

**Example:**
```bash
python3 scripts/inject_model.py \
  references/claims-fraud.json \
  /mnt/skills/user/graph-schema-editor/assets/graph-editor-template.jsx \
  /mnt/user-data/outputs/graph-schema-editor.jsx
```

This reads the reference model JSON, extracts its `initialGraph` (nodes, relationships,
positions, colors, properties), and injects it into the schema editor template. The output
is a ready-to-use JSX artifact.

### Step 3: Present the artifact

Present `/mnt/user-data/outputs/graph-schema-editor.jsx` to the user and briefly explain:
- The editor is pre-loaded with the **{model name}** reference model from Neo4j's documentation
- Source: {link from the model JSON's description field}
- They can add/remove nodes, edit properties, create relationships interactively
- Double-click canvas to add nodes, drag from node edge to create relationships
- Export to arrows.app JSON or Cypher via the Export button

## Available Reference Models

Read `references/model-index.json` for the full catalog with tags and descriptions.

### Financial Services (11 models)

| ID | Name | Nodes | Rels |
|----|------|-------|------|
| `transaction-base-model` | Transaction & Account Base Model | 19 | 24 |
| `fraud-event-sequence` | Fraud Event Sequence Model | 13 | 26 |
| `regulatory-dependency-mapping` | Regulatory Dependency Mapping | 2 | 3 |
| `mutual-fund-dependency` | Mutual Fund Dependency Analytics | 3 | 2 |
| `deposit-analysis` | Deposit Analysis | 5 | 5 |
| `account-takeover-fraud` | Account Takeover Fraud | 8 | 7 |
| `automated-facial-recognition` | Automated Facial Recognition | 5 | 4 |
| `synthetic-identity-fraud` | Synthetic Identity Fraud | 5 | 5 |
| `transaction-fraud-ring` | Transaction Fraud Ring | 2 | 2 |
| `transaction-monitoring` | Transaction Monitoring | 7 | 7 |
| `transaction-fraud-detection` | Transaction Fraud Detection (IEEE-CIS) | 6 | 5 |

### Insurance (2 models)

| ID | Name | Nodes | Rels |
|----|------|-------|------|
| `claims-fraud` | Insurance Claims Fraud | 4 | 5 |
| `quote-fraud` | Insurance Quote Fraud | 1 | 1 |

### Healthcare & Life Sciences (5 models)

| ID | Name | Nodes | Rels |
|----|------|-------|------|
| `patient-journey` | Patient Journey | 7 | 8 |
| `patent-intelligence` | Patent Intelligence | 6 | 7 |
| `publication-intelligence` | Publication Intelligence | 6 | 6 |
| `single-omics` | Single-omics Data Integration | 6 | 7 |
| `multi-omics` | Multi-omics Data Integration | 8 | 9 |

### Manufacturing (4 models)

| ID | Name | Nodes | Rels |
|----|------|-------|------|
| `ev-route-planning` | Electric Vehicle Route Planning | 4 | 5 |
| `configurable-bom` | Configurable Bill of Materials | 6 | 7 |
| `engineering-traceability` | Engineering Traceability | 6 | 7 |
| `process-monitoring-cpa` | Process Monitoring & Critical Path Analysis | 6 | 6 |

### Cybersecurity (3 models)

| ID | Name | Nodes | Rels |
|----|------|-------|------|
| `vulnerability-prioritization` | Vulnerability Prioritization & Exposure Management | 6 | 6 |
| `attack-path-analysis` | Attack Path Analysis | 7 | 8 |
| `software-supply-chain-security` | Software Supply Chain Security | 6 | 6 |

## Model Routing Guide

Use these keywords to pick the right model:

- **Banking / payments / KYC** → `transaction-base-model`
- **Fraud detection (account takeover)** → `account-takeover-fraud` or `fraud-event-sequence`
- **Fraud rings / circular transactions** → `transaction-fraud-ring`
- **AML / compliance** → `transaction-monitoring`
- **Insurance claims** → `claims-fraud`
- **Insurance quotes / ghost broking** → `quote-fraud`
- **Healthcare / clinical** → `patient-journey`
- **Pharma R&D** → `single-omics` or `multi-omics`
- **Pharma competitive intel** → `patent-intelligence` or `publication-intelligence`
- **Manufacturing BOM** → `configurable-bom`
- **Supply chain / EV logistics** → `ev-route-planning`
- **Production scheduling** → `process-monitoring-cpa`
- **Cyber vulnerability / CVE** → `vulnerability-prioritization`
- **Penetration testing / lateral movement** → `attack-path-analysis`
- **SBOM / software dependencies** → `software-supply-chain-security`
- **Regulatory compliance** → `regulatory-dependency-mapping`
- **Investment / fund analysis** → `mutual-fund-dependency`

## How inject_model.py Works

The script in `scripts/inject_model.py`:

1. Reads the reference model JSON file
2. Extracts the `initialGraph` object (nodes with positions/colors/properties, relationships)
3. Converts it to a JavaScript `const initialGraph = { ... };` declaration
4. Reads the graph-schema-editor template JSX
5. Replaces the existing `const initialGraph = { ... };` block via regex
6. Writes the combined output to the specified path

The reference model colors are hex strings (e.g. `"#68BC00"`) which work directly in the
editor's style system — no COLORS array reference needed.

## Important Notes

- Always use the inject script rather than manually editing the template
- The `initialGraph` format is arrows.app-compatible — exports work with Neo4j tooling
- Property types use Neo4j conventions: `string`, `integer`, `float`, `boolean`, `date`,
  `datetime`, `list_of_float`
- Models with `extends` build on another model — mention this to the user
- If a model JSON includes `constraints` and `indexes` arrays, share those with the user
  as additional Cypher they can apply to their Neo4j instance
