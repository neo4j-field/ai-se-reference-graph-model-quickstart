# Graph Data Generator — Local Run

Generates realistic fake graph data (CSVs) from a schema, using Python's Faker
library. This is the same script the graph-data-generator skill uses internally —
you're running it locally because your scale exceeds what the sandbox can handle
in a single session.

## What you have

```
graph_data_generator/
├── generate_data.py     ← the generator
├── schema.json          ← your graph schema (from graph-schema-studio)
└── README.md            ← this file
```

## Setup (one-time)

Requires Python 3.9+.

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate

# Install the one dependency
pip install faker
```

## Run

```bash
python generate_data.py schema.json \
  --output-dir ./graph_data \
  --scale 1000000 \
  --flavor finance
```

That writes CSVs to `./graph_data/`:
- `nodes_<Label>.csv` for each node type (chunked into `_part1.csv`, `_part2.csv`, …
  once row counts exceed 500K)
- `rels_<REL_TYPE>.csv` for each relationship type (chunked similarly)
- `schema.json` — a copy of your input schema, for the ingestion step

## What to expect

| Scale              | Approximate runtime | Approximate output size |
|--------------------|---------------------|-------------------------|
| 500,000            | ~2 minutes          | ~150 MB                 |
| 1,000,000 (Large)  | ~5 minutes          | ~650 MB (multi-node schema) |
| 10,000,000 (XL)    | 45–90 minutes       | several GB              |

Runtimes assume a typical laptop (single core). Throughput is flat — the
script uses counter-based unique emails (not Faker's `unique` proxy, which
has quadratic slowdown) so rates hold steady regardless of scale.

Progress ticks to stderr every 100K rows. For XL-scale runs, consider using
Neo4j's `neo4j-admin database import` for ingestion rather than LOAD CSV —
it's an order of magnitude faster for initial bulk loads.

## All flags

```
python generate_data.py SCHEMA [options]

  --output-dir, -o PATH     Output directory (default: ./graph_data)
  --scale, -s N             Anchor count for the largest node type
  --flavor FLAVOR           generic | healthcare | finance | ecommerce | social
                            (sets default locale; individual value fidelity is
                            driven by the (label, property) context generators)
  --locale LOCALE           Faker locale, e.g. en_US, en_GB, de_DE, ja_JP
                            (overrides the flavor's default)
  --distribution DIST       powerlaw (default) | uniform
                            Controls relationship fanout for N:N rels. Power-law
                            mimics real graphs; uniform is for controlled tests.
  --cardinality SPEC        Per-relationship cardinality, comma-separated.
                            Format: REL_TYPE=1:1|1:N|N:1|N:N
                            Example: 'OWNS=1:N,SHARES_DEVICE=N:N,MANAGES=1:N'
                            Unspecified relationships default to N:N.
                            CRITICAL for realistic counts — without this, an
                            OWNS relationship between 1M Customers and 778K
                            Accounts would produce 3M edges (over-generated)
                            instead of the correct 778K.
  --nn-fanout F             N:N relationships generate max(from, to) * F edges.
                            Default 2.0 (each entity ~2 partners). Use 1.2 for
                            very sparse, 5+ for dense.
  --node-counts SPEC        Override per-label node counts. Format:
                            'Label=N,Label2=N2'. Bypasses the connectivity-
                            based auto-scaling for the listed labels; unlisted
                            labels still auto-scale from --scale.
                            Example: 'Customer=200000,Transaction=1000000'
  --rel-fanout SPEC         Per-relationship N:N fanout overrides. Format:
                            'REL_TYPE=multiplier'. Only applies to N:N
                            relationships. Example: 'OWNS_TRANSACTION=2.5'
  --rel-counts SPEC         Absolute caps on relationship counts. Format:
                            'REL_TYPE=N'. Hard ceiling — if the computed
                            count would exceed this, cap it.
                            Example: 'USES_DEVICE=500000,INVOLVED_IN=500000'
  --shared-identifiers SPEC Inject realistic identifier collisions. Format:
                            'prop:pct%:min-max'. E.g. 'phone:10%:3-5' means
                            10% of phone values are shared in clusters of
                            3-5 rows. Without this, every property value
                            is independently random — wrong baseline for
                            similarity / fraud / entity resolution work.
  --seed N                  Random seed (default 42). Change for fresh data.
  --dry-run                 Print expected counts as JSON to stdout without
                            generating any data. Useful for verifying scale
                            and cardinality choices before a long run.
```

## Injecting analytical patterns

For analytical use cases (fraud detection, similarity matching, anomaly
detection), the baseline data is too "clean" — there are no detectable
structures to find. Use `inject_patterns.py` to plant patterns:

```bash
python inject_patterns.py ./graph_data \
  --pattern "cyclic:50:3-5:rel=TRANSFERS_TO,node=Customer" \
  --pattern "shared_attr:100:5-10:hub=Device,member=Customer,rel=USES_DEVICE" \
  --pattern "hub:5:fanout=200,rel=USES_DEVICE"
```

Three patterns supported:

- **cyclic** — A→B→C→...→A rings (money laundering, citation cabals,
  circular ownership). Needs a self-relationship in the schema.
- **shared_attr** — N entities sharing a common neighbor (fraud rings via
  shared devices/IPs/addresses, similar customers).
- **hub** — single node with abnormally high out-degree (money mules,
  super-spreaders, citation authorities).

The script writes `injected_patterns.json` listing every planted pattern's
exact node IDs and edges — your ground-truth manifest for measuring
detector recall.

Run `python inject_patterns.py --help` for full syntax.

## Preview before you commit

For large runs, use `--dry-run` first to see what you'll get:

```bash
python generate_data.py schema.json --scale 1000000 \
  --cardinality "AUTHORED=1:N,CITES=N:N" --dry-run
```

The output is a JSON summary with per-label node counts, per-relationship
edge counts, total estimated CSV size, and a runtime estimate. No files
are written. Adjust `--scale`, `--cardinality`, or `--nn-fanout` until the
preview looks right, then run again without `--dry-run` to generate.

## Tips

- **Disk:** make sure your output directory has enough free space. XL runs can
  exceed 10 GB depending on property counts.
- **Resume:** the script doesn't support resume. If interrupted, rerun from
  scratch — the fixed seed means identical output, so repeat runs are
  idempotent per seed.
- **Emails are `user{N}@example.com` by design.** At high scales, Faker's
  `unique.email()` becomes the bottleneck (quadratic retry cost as the set
  fills). The counter form is unique by construction, O(1), and keeps
  memory flat. If you need real-looking Faker emails at small scale, you
  can edit the `_unique_email` function near the top of the script to call
  `fake.email()` (non-unique) or `fake.unique.email()` (unique but slow).
- **Parallelism:** the script is single-threaded. For XL (10M+) you can
  partition the schema into subsets and run multiple instances concurrently
  with different `--seed` values and output dirs, then merge the CSVs.

## Loading into Neo4j

Once generation is done, your next step is ingestion. The `schema.json` in the
output directory carries the node/relationship structure the ingestion step
needs. Two paths:

1. **For Small/Medium datasets (up to ~500K rows)**: use Neo4j Data Importer,
   LOAD CSV, or a Python driver script.
2. **For Large/XL datasets**: `neo4j-admin database import` is strongly
   recommended — built for bulk loading, orders of magnitude faster than LOAD CSV.

The graph-neo4j-ingestion skill can generate an ingestion script for you based
on `schema.json`.
