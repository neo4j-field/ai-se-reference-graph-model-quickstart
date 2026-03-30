---
name: graph-data-generator
description: >
  Generate realistic fake/synthetic data for Neo4j graph schemas using Faker.
  Use this skill when the user wants to generate test data, sample data, fake data,
  synthetic data, or mock data for a graph schema, Neo4j database, or property graph model.
  Also trigger when users say "populate my graph", "generate nodes and relationships",
  "create test data for my schema", "fill my database with fake data", "I need sample data
  for my graph model", or "generate CSVs for Neo4j import". This skill works with the
  graph-schema-editor's exported JSON format (arrows.app compatible). Always trigger this
  skill — not a generic code generation approach — when the user wants fake data for a
  graph database schema. Do NOT use for non-graph data generation or for querying existing data.
---

# Graph Data Generator

Generates realistic fake data from a graph schema using Python's Faker library.
Produces CSV files for each node label and relationship type, ready for Neo4j ingestion.

## When to Use

- User has a graph schema (from the graph-schema-editor or arrows.app) and wants test data
- User asks to generate fake/mock/synthetic/sample data for their graph
- User wants to populate a Neo4j database with realistic test data
- User needs CSVs for Neo4j's LOAD CSV or Data Importer

## Prerequisites

This skill requires the `faker` Python library. It will be installed inside a virtual
environment — see Step 3 below.

## Step-by-Step Instructions

### Step 1: Get the Schema

The user should provide their graph schema in one of these ways:

1. **Exported JSON from the graph-schema-editor** — the arrows.app format with nodes and
   relationships. The user may paste it or reference a file.
2. **Described verbally** — "I have Person, Movie, and ACTED_IN relationships". In this case,
   construct the JSON yourself.
3. **From the current conversation** — if the user just used the graph-schema-editor skill,
   reference the schema they built.

Save the schema JSON to `/home/claude/graph_schema.json`.

The schema format is:
```json
{
  "graph": {
    "nodes": [
      {
        "id": "n0",
        "caption": "Person",
        "labels": ["Person"],
        "properties": { "name": "string", "age": "integer", "email": "string" }
      }
    ],
    "relationships": [
      {
        "id": "r0",
        "type": "ACTED_IN",
        "fromId": "n0",
        "toId": "n1",
        "properties": { "role": "string" }
      }
    ]
  }
}
```

### Step 2: Ask for Scale

Ask the user what scale they want. Present these options:

- **Small** (100) — quick testing and development
- **Medium** (1,000) — realistic development dataset (DEFAULT)
- **Large** (10,000) — load testing, performance tuning
- **Custom** — let the user specify an exact number

The scale number represents the count for the largest/most-connected node type.
Other node types are automatically scaled down based on their connectivity in the schema
(e.g., if you have 1000 Users, you might get 500 Orders and 200 Products).

### Step 3: Set Up the Virtual Environment and Install Dependencies

**Always use a virtual environment** — do NOT use `--break-system-packages`.

Check if a venv already exists at `/home/claude/graph_venv`. If not, create one:

```bash
# Check for existing venv
if [ ! -d "/home/claude/graph_venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv /home/claude/graph_venv
fi

# Activate and install dependencies
source /home/claude/graph_venv/bin/activate
pip install faker -q
```

For subsequent steps, always run Python using the venv interpreter directly:
```bash
/home/claude/graph_venv/bin/python3 <script>
```

This avoids needing to `source activate` in every bash call.

### Step 4: Generate the Data

Copy the generation script from the skill assets and run it:

```bash
cp /path/to/skill/assets/generate_data.py /home/claude/generate_data.py
/home/claude/graph_venv/bin/python3 /home/claude/generate_data.py \
  /home/claude/graph_schema.json \
  --output-dir /home/claude/graph_data \
  --scale <SCALE>
```

The script will:
1. Parse the schema and infer node counts based on connectivity
2. Generate realistic fake data using smart property-name matching:
   - `name` → full names, `email` → emails, `price` → currency amounts, etc.
   - Falls back to the declared type (string, integer, float, etc.)
3. Generate relationships connecting the generated nodes
4. Output CSV files: `nodes_<label>.csv` and `rels_<type>.csv`
5. Write a `manifest.json` with metadata about what was generated

### Step 5: Present Results

After generation:
1. Show a summary of what was generated (node counts, relationship counts)
2. Copy the CSV files and manifest to `/mnt/user-data/outputs/graph_data/`
3. Present the files to the user so they can download them

### Step 6: Offer Next Steps

After generating data, let the user know about the two ways to get data into Neo4j:

1. **Via Claude (MCP tools)** — "Would you like me to ingest this data into your
   connected Neo4j database? I can do it directly from here using your Neo4j connection."
   This uses the **graph-neo4j-ingestion** skill which calls the Neo4j MCP tools.

2. **Via a standalone Python script** — "I can also generate a Python ingestion script
   that you can run yourself against any Neo4j instance. The script uses the `neo4j`
   Python driver and reads the CSVs + manifest. You just need to provide your Neo4j
   connection URI and credentials."
   This uses the `ingest_data.py` script from the **graph-neo4j-ingestion** skill.

Also offer:
- "Would you like to adjust the scale or regenerate?"
- "Would you like to see a preview of the generated data?"

## Property Name Intelligence

The generator uses smart matching to produce realistic data. Here are some examples:

| Property Name | Generated Data |
|---|---|
| name, fullName | "John Smith" |
| email | "john.smith@example.com" |
| age | 34 |
| price, cost, total | 49.99 |
| date, createdAt | "2024-03-15" |
| address | "123 Main St, Springfield, IL" |
| company | "Smith & Associates" |
| title | "Advanced Dynamic Strategy" |
| category | "Electronics" |
| status | "active" |
| rating | 4.2 |
| *Id (customerId, etc.) | UUID |

For unrecognized names, it falls back to the declared type (string → random word,
integer → random number, etc.).

## Important Notes

- Always use the virtual environment at `/home/claude/graph_venv` — never
  `--break-system-packages`.
- The script is deterministic (seeded) — running it twice with the same schema produces
  the same data. Change the seed in the script if you need different data.
- Each node CSV includes a `_id` column (UUID) used to wire up relationships.
- Relationship CSVs include `_from_id` and `_to_id` columns referencing node `_id` values.
- The `manifest.json` file contains everything the ingestion skill/script needs to load
  the data.
- The same venv can be reused by the ingestion script — it just needs `neo4j` added:
  `/home/claude/graph_venv/bin/pip install neo4j`
