# graph-data-workflow — install

A small, conversational skill: ask the user the right questions about
their schema, then write a Faker script tailored to the answers.

## Files in this package

```
graph-data-workflow/
├── SKILL.md                       ← router (1016 chars, under 1024 limit)
├── INSTALL.md                     ← this file
├── assets/
│   └── docs/
│       └── WORKFLOW.md            ← the 6-step Q&A flow
└── scripts/
    └── build_script.py            ← templater: config.json → standalone generate.py
```

## How it works

There are no domain packs, no fingerprint tables, no canned reference
data. Claude reads the user's schema in conversation, proposes 3-4
plausible use cases as `ask_user_input_v0` options, and walks through
six steps: **scale → use case → cardinality → preview → patterns →
script.**

At the end, `build_script.py` takes a single config JSON (built up
across the steps) and emits a standalone `generate.py`. The user can
re-run that script on their laptop with `pip install faker && python
generate.py` — no external dependencies beyond Faker.

## Where to put it

Drop `graph-data-workflow/` into your skills directory.

## Dependencies

- Python 3.9+
- `faker` (only needed at script-run time, not at build time)

## Quick smoke test

```bash
SKILL=/path/to/graph-data-workflow

# Build a config (in real use, Claude builds this from the conversation)
cat > /tmp/run_config.json <<'CFG'
{
  "anchor_label": "Customer",
  "anchor_count": 200,
  "use_case": "fraud detection",
  "schema_path": "/path/to/your/schema.json",
  "cardinality": {
    "OWNS": {"from": "Customer", "to": "Account", "kind": "1:N", "avg": 2.5}
  },
  "property_generators": {
    "Customer.name": {"type": "faker", "method": "name"}
  },
  "patterns": [],
  "output_dir": "/tmp/data",
  "seed": 42
}
CFG

# Build the standalone script
python3 $SKILL/scripts/build_script.py /tmp/run_config.json /tmp/generate.py

# Run it
pip install faker
python3 /tmp/generate.py
ls /tmp/data/
```

## Patterns supported

Three pattern types are built in. The skill validates each against the
schema before planting (e.g. `cyclic` requires a self-relationship).

- **`cyclic`** — A→B→C→...→A rings on a single node label.
  Spec: `{"type": "cyclic", "count": 50, "ring_size": [3, 5], "rel": "TRANSFERS_TO", "node": "Customer"}`
- **`shared_attr`** — N members linked to one shared hub.
  Spec: `{"type": "shared_attr", "count": 100, "cluster_size": [5, 10], "hub": "Device", "member": "Customer", "rel": "USES"}`
- **`hub`** — A few nodes with abnormally high out-degree.
  Spec: `{"type": "hub", "count": 5, "fanout": 200, "rel": "TRANSFERS_TO"}`

All patterns are recorded in `injected_patterns.json` with the exact
node IDs that participated, so the user can verify their detection
queries against ground truth.

## Generator types supported in property_generators

- `faker` — `{type, method, args?}` — calls Faker
- `categorical` — `{type, values, weights?}` — random choice with weights
- `regex` — `{type, pattern}` — regex-like fill (supports `[A-Z]{n}`, ranges, literals)
- `lognormal` — `{type, mu, sigma, min?, max?, round_to?}`
- `normal` — `{type, mean, std, min?, max?, round_to?}`
- `uniform` — `{type, min, max, integer?, round_to?}`
- `sequence` — `{type, prefix, start?, pad_width?}` — counter like `CUST0000001`
- `datetime` — `{type, start, end, format?}` — accepts `today`, `today-3y`, ISO dates
- `derived` — `{type, from, transform}` — computed from another property
  - transforms: `email_from_name`, `domain_from_email`
- `constant` — `{type, value}`

When a property has no generator, a small heuristic fallback applies
(`email` → fake email, `*Id` → UUID, type-based defaults otherwise).
This is the only inference; everything else is explicit in the config.

## Replaces

- `graph-data-generator` — older skill with hardcoded property tables
- `graph-neo4j-ingestion` — older ingestion skill

Both should still be on disk marked deprecated. If you want to remove
them, delete `/mnt/skills/user/graph-data-generator/` and
`/mnt/skills/user/graph-neo4j-ingestion/`.
