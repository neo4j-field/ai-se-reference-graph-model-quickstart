---
name: graph-schema-studio
description: >
  Design, visualise, and edit Neo4j property graph schemas as interactive React artifacts.
  Use whenever the user wants to design, create, draw, model, or visualise a graph schema,
  graph data model, Neo4j schema, property graph model, or node-relationship diagram.
  Handles both custom domains ("design a schema for my e-commerce system") and 32 pre-built
  Neo4j reference models across Financial Services, Insurance, Healthcare & Life Sciences,
  Manufacturing, Cybersecurity, and Industry Agnostic use cases. Trigger for "design a
  graph schema", "Neo4j data model", "property graph", "arrows.app diagram", "reference
  model", "industry template", "start from the claims fraud model", "patient journey
  schema", "CMDB", "IAM effective access", "entity resolution", "UBO", "FAERS drug
  safety", "BOM", or any Neo4j use case. Also trigger when the user uploads an arrows.app
  JSON or reference-model JSON. Do NOT trigger for graph charts (bar/line/pie),
  mathematical graphs, or visualising query results.
---

# Graph Schema Studio

Generate an interactive React artifact that lets the user visually design a Neo4j property
graph schema — nodes, relationships, labels, and properties — directly in the chat. Works
from a blank custom domain, from one of 32 pre-built Neo4j reference models, or from a JSON
the user uploads.

## The one command you will run

Every path goes through a single script:

```bash
python3 /mnt/skills/user/graph-schema-studio/scripts/inject.py <input> [output.jsx]
```

The script auto-detects what `<input>` is:

- **A reference model id** (e.g. `claims-fraud`, `patient-journey`) → loads from the bundled catalog
- **A file path** (e.g. `/home/claude/my_schema.json`) → reads that file directly
- **Missing or `-`** → reads JSON from stdin (the usual "cat heredoc | inject.py" pattern)
- **`--list`** → prints the reference-model catalog
- **`--help`** → prints usage

Default output is `/mnt/user-data/outputs/graph-schema-editor.jsx`. Pass a `.jsx` path as the
second argument to override.

**Why one script matters:** the React template is ~650 lines. Regenerating it token-by-token
for every schema is slow and wasteful. The injector lets you produce only the ~10–30 lines of
JSON that describe the domain — the editor itself is already on disk.

## Pick the right path

Match the user's situation:

- **User named a reference model** ("start from the claims fraud model", "load UBO schema")
  → run `inject.py <model-id>`. See *Reference model catalog* below for the id list.
- **User uploaded arrows.app JSON or reference-model JSON**
  → run `inject.py /path/to/file.json`. The script auto-unwraps `{graph: {...}}` and
  `{initialGraph: {...}}` containers, so uploaded files typically work unchanged.
- **User described a custom domain** ("e-commerce", "music streaming", "my manufacturing
  process") → write a minimal schema JSON (see *Minimal schema shape*) and pipe it via stdin.
- **Domain is unclear** ("help me model my business") → ask ONE clarifying question before
  injecting. Never ship the default example.

## Custom domains: the stdin pattern

```bash
cat <<'EOF' | python3 /mnt/skills/user/graph-schema-studio/scripts/inject.py
{
  "nodes": [
    { "caption": "Customer", "properties": { "customerId": "string", "name": "string", "email": "string" } },
    { "caption": "Order",    "properties": { "orderId": "string", "total": "float" } },
    { "caption": "Product",  "properties": { "sku": "string", "price": "float" } }
  ],
  "relationships": [
    { "type": "PLACED",   "from": "Customer", "to": "Order" },
    { "type": "CONTAINS", "from": "Order",    "to": "Product", "properties": { "quantity": "integer" } }
  ]
}
EOF
```

For more complex or reusable schemas, save the JSON first and pass the path:

```bash
cat > /home/claude/my_schema.json <<'EOF'
{ "nodes": [...], "relationships": [...] }
EOF
python3 /mnt/skills/user/graph-schema-studio/scripts/inject.py /home/claude/my_schema.json
```

## Minimal schema shape

Each **node** needs only `caption`. Supply `properties` when you have them. Everything else
is filled in automatically so you can stay terse.

| Field | Required? | Default when omitted |
|-------|-----------|----------------------|
| `caption` | yes | — |
| `properties` | no | `{}` |
| `id` | no | `n0`, `n1`, … |
| `position` | no | Circular auto-layout centred on the viewport |
| `labels` | no | `[caption]` — see *Multi-label nodes* below |
| `style.color` | no | Cycled through a 10-colour palette |
| `style.radius` | no | `55` |

Each **relationship** needs `type`, and either `from`/`to` (caption lookup) or
`fromId`/`toId` (explicit ids — required when two nodes share a caption).

| Field | Required? | Notes |
|-------|-----------|-------|
| `type` | yes | UPPER_SNAKE_CASE, e.g. `ACTED_IN` |
| `from` or `fromId` | yes | Caption lookup OR explicit id |
| `to` or `toId` | yes | Caption lookup OR explicit id |
| `properties` | no | `{}` |
| `id` | no | `r0`, `r1`, … |

Any field you supply is respected unchanged — mix fully-specified nodes with minimal ones
freely. Use explicit positions when the user asks for a specific layout, explicit colours
to group nodes visually, explicit ids when captions would collide.

## Multi-label nodes

Neo4j supports multiple labels per node — a common pattern is a primary label plus a
type discriminator, e.g. `:Account:Internal` vs `:Account:External`, or
`:Event:Authentication`. Supply a `labels` array with more than one entry:

```json
{
  "nodes": [
    { "caption": "Account", "labels": ["Account", "Internal"], "properties": { "accountNumber": "string" } },
    { "caption": "Account", "labels": ["Account", "External"], "properties": { "accountNumber": "string" } }
  ],
  "relationships": [
    { "type": "TRANSFERRED_TO", "fromId": "n0", "toId": "n1" }
  ]
}
```

**Invariants the injector enforces:**
- `caption` is always the first element of `labels`. If the user supplies labels out of
  order (caption not first), the injector reorders them; in the editor UI the caption
  field drives the primary label.
- Duplicates and empty/whitespace-only labels are dropped during normalisation.
- Relationship endpoints cannot be resolved by caption when two nodes share one — use
  explicit `fromId`/`toId` as in the example above.

**What renders on the canvas:** the caption is shown big inside the circle, and any
additional labels appear as small pills directly below the circle (arrows.app convention),
styled in the node's colour so they read as "part of the node". Properties continue below
the pills.

**What the user edits:** the Inspector has a "Caption (primary label)" field and a
comma-separated "Additional labels" field. Editing either preserves the other —
changing `"Account"` to `"BankAccount"` keeps `Internal` intact.

**What the exports produce:**
- Cypher: `CREATE (n1:Account:Internal {...})`
- arrows.app JSON: the full `labels` array is preserved unchanged.

## Accepted wrapping formats

The injector unwraps these automatically, so user-uploaded files work without preprocessing:

- Bare: `{ "nodes": [...], "relationships": [...] }`
- arrows.app: `{ "graph": { "nodes": [...], "relationships": [...] } }`
- Reference model: `{ "initialGraph": { "nodes": [...], "relationships": [...] }, ... }`

## Reference model catalog

Run `inject.py --list` for the live catalog. Quick keyword map:

### Financial Services (13)

| Keyword | Model id |
|---------|----------|
| banking, transactions, KYC, base model | `transaction-base-model` |
| fraud event sequence | `fraud-event-sequence` |
| regulatory, compliance | `regulatory-dependency-mapping` |
| mutual fund, investment | `mutual-fund-dependency` |
| deposit | `deposit-analysis` |
| account takeover, ATO | `account-takeover-fraud` |
| facial recognition, biometric | `automated-facial-recognition` |
| synthetic identity | `synthetic-identity-fraud` |
| fraud ring, circular payments | `transaction-fraud-ring` |
| transaction monitoring, AML | `transaction-monitoring` |
| IEEE-CIS, fraud detection ML | `transaction-fraud-detection` |
| customer churn, retention, dormancy | `customer-churn` |
| UBO, beneficial owner, 6AMLD | `ubo-company-ownership` |

### Insurance (2)

| Keyword | Model id |
|---------|----------|
| insurance claims, crash for cash | `claims-fraud` |
| insurance quote, ghost broker | `quote-fraud` |

### Healthcare & Life Sciences (7)

| Keyword | Model id |
|---------|----------|
| patient journey, healthcare, OMOP | `patient-journey` |
| patent, IP intelligence | `patent-intelligence` |
| publication, KOL | `publication-intelligence` |
| pharma pipeline, clinical trials landscape | `pipeline-intelligence` |
| drug safety, pharmacovigilance, FAERS, DDI | `drug-safety` |
| single-omics, genomics | `single-omics` |
| multi-omics | `multi-omics` |

### Manufacturing (4)

| Keyword | Model id |
|---------|----------|
| EV, route planning | `ev-route-planning` |
| BOM, bill of materials, CBOM | `configurable-bom` |
| traceability, requirements, test cases | `engineering-traceability` |
| process monitoring, critical path | `process-monitoring-cpa` |

### Cybersecurity (3)

| Keyword | Model id |
|---------|----------|
| vulnerability, CVE, VPEM | `vulnerability-prioritization` |
| attack path, lateral movement | `attack-path-analysis` |
| SBOM, software supply chain | `software-supply-chain-security` |

### Industry Agnostic (3)

| Keyword | Model id |
|---------|----------|
| entity resolution, record linkage | `entity-resolution` |
| CMDB, IT service graph, infrastructure | `it-service-graph` |
| IAM, RBAC, effective access | `iam-effective-access` |

When a reference model is injected, the script surfaces its name and source URL — share
these with the user so they know what they're looking at and can dig deeper if needed.
Some reference models include `constraints`, `indexes`, or `notes` fields; when present,
mention them briefly when presenting the artifact.

## Presenting the result

Call `present_files` on `/mnt/user-data/outputs/graph-schema-editor.jsx` and briefly orient
the user. Keep it short:

- Double-click the canvas (or click "Add Node") to add nodes
- Drag from a node's edge to another node to create a relationship
- Click any element to edit it in the sidebar — label, properties, colour, radius
- Scroll wheel zooms; drag the canvas to pan
- Export → arrows.app JSON or Cypher

## What comes next

After the user customises the schema, the typical next steps live in other skills:

- **Generate fake data** from the schema → `graph-data-generator` skill
- **Load that data into a Neo4j instance** → `graph-neo4j-ingestion` skill

When the user signals they're done editing ("done", "looks good", "generate data"),
capture their exported arrows.app JSON if they pasted one, save it to
`/home/claude/graph_schema.json`, and hand off to `graph-data-generator`.

## Fallback: editing the template directly

If the injector script fails to run (it shouldn't, but check with `ls` if things look wrong),
you can hand-edit `assets/graph-editor-template.jsx` by replacing the
`const initialGraph = { ... };` block at the top. This generates hundreds of lines of JSX
token-by-token and is significantly slower — always prefer the injector.

## Other notes

- The artifact is self-contained — no external dependencies beyond React, which the Claude
  artifact runtime provides.
- Exported arrows.app JSON opens in arrows.app and in tools like Neo4j Runway.
- Exported Cypher produces `CREATE` statements that run directly in Neo4j Browser.
- Reference models preserve their curated positions and colours verbatim — those were
  tuned by Neo4j for readability, so let the user move things around rather than
  re-laying them out yourself.
