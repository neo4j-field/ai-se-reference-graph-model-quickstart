# Workflow — six conversational steps

The whole skill is a conversation. Claude reads the user's schema, asks
the right questions in order, and at the end produces a runnable Python
script that uses Faker to populate the graph.

There are no domain packs, no fingerprint tables, and no canned
reference data. Claude reasons about each schema fresh, proposes options
based on what's actually in the labels and relationships, and lets the
user steer.

## The shape of the flow

```
Step 1   Ask about scale          (4 options + custom)
Step 2   Confirm use case         (3-4 options inferred from schema)
Step 3   Propose cardinality      (table; user can edit any row)
Step 4   Show data preview        (sample rows + total counts)
Step 5   Ask about patterns       (menu inferred from use case)
Step 6   Write & run script       (standalone Faker script + CSV outputs)
```

Each step ends in a pause. Claude does not guess the user's answer or
proceed without confirmation.

## Before Step 1: get the schema

The user provides a schema in one of these ways:

1. **Arrows.app JSON** — uploaded file, or content from a previous
   graph-schema-studio session. Save to `/home/claude/graph_schema.json`.
2. **Described in conversation** — labels and relationships in prose.
   Build the JSON yourself and save it.
3. **Reference to a graph-schema-studio model** — copy from
   `/mnt/skills/user/graph-schema-studio/references/<id>.json`.

The expected format is:

```json
{
  "graph": {
    "nodes": [
      {"id": "n0", "labels": ["Customer"], "properties": {"name": "string", "email": "string"}}
    ],
    "relationships": [
      {"id": "r0", "type": "OWNS", "fromId": "n0", "toId": "n1", "properties": {}}
    ]
  }
}
```

`{initialGraph: {...}}` and `{nodes: [...], relationships: [...]}` (no
wrapper) also work. Don't proceed to Step 1 until you have the schema
parsed and you can list the labels and relationship types.

---

## Step 1: ask about scale

Ask first because everything else scales from this number. The "anchor
count" means: how many of the *primary* node should exist. For
fraud-style schemas the anchor is usually `Customer` or `Account`; for
e-commerce, `Customer` or `Order`; for healthcare, `Patient`. Claude
should infer the anchor label and name it in the question.

Use `ask_user_input_v0` with these options:

```
How much data should I generate? (Anchor: <Label>)
  • 10,000           ← recommended for analytics + iteration
  • 100,000          ← realistic load
  • 1,000,000        ← performance testing
  • Custom           ← tell me a number
```

Wait for the answer. If the user picks Custom, ask for the number as a
follow-up.

**Don't skip this step even if the user already mentioned a number in
passing.** A number in passing isn't a confirmed choice.

---

## Step 2: confirm the use case

This is where Claude reasons about the schema. **Do not look anything
up.** Read the labels, the relationship types, and any property names
that hint at domain. Propose **3-4 plausible use cases** as options,
plus "generic test data" as a safe fallback. The proposals must be
specific to the actual schema — not a generic menu.

Examples of how to reason:

| Schema labels | Proposed use cases |
|---|---|
| `Customer + Account + Transaction + Device` | Fraud detection (rings, money-mule patterns); AML / structuring; Customer 360 / churn analytics; Generic banking test data |
| `Patient + Provider + Claim + Diagnosis` | Insurance claims fraud; Clinical analytics / patient journey; Provider quality scoring; Generic healthcare test data |
| `User + Post + Like + Follow` | Social network analytics (community detection); Recommendation system; Spam / bot detection; Generic social test data |
| `Component + Assembly + Supplier` | Supply chain risk analysis; Bill-of-materials / dependency analysis; Supplier consolidation analytics; Generic manufacturing test data |

Frame the question as "which of these matches what you're doing" — not
"what are you doing" (open question). The user is more likely to give a
useful steer if they're picking from a concrete list. Always include an
"other / let me describe it" option as the off-ramp.

Use `ask_user_input_v0`. After the user picks, restate the use case in
one sentence so they can correct any misreading before Step 3.

If the user picks "other", ask them to describe it in one or two
sentences and use that description as the use case throughout.

---

## Step 3: propose cardinality

Walk every relationship in the schema. For each one, propose a sensible
cardinality and an average fanout, **with brief reasoning tied to the
chosen use case**. Show as a markdown table the user can edit row by row.

The reasoning matters. "1 Customer → 2.5 Accounts" is more useful when
followed by "(retail customers usually have a current + savings, some
also have ISA/business)" than as a bare number.

Format:

> **Cardinality proposal** — given <use case>, I'd suggest:
>
> | Relationship                     | Direction & average        | Reasoning |
> |----------------------------------|----------------------------|-----------|
> | `Customer -[OWNS]-> Account`     | 1 Customer : 2.5 Accounts  | Retail customers typically hold a current + savings, sometimes ISA |
> | `Account -[PERFORMS]-> Transaction` | 1 Account : 250 Transactions | A year of activity at low transaction velocity |
> | `Customer -[USES]-> Device`      | N:N, avg 1.3 devices/customer | Most have one phone; some have phone + laptop |
> | `Customer -[TRANSFERS_TO]-> Customer` | N:N, avg 5 outgoing per customer | Sparse social-of-payments graph |
>
> Edit any row by saying "make USES 2 devices on average" or "Account to
> Transaction should be 50, not 250", or accept the whole table.

Pause. Loop on edits — re-render the full updated table after each
change so the user always sees the current state. Don't move on until
the user accepts.

### Cardinality heuristics Claude can use

These are guidelines, not rules. Adjust based on the specific use case.

- Names like `OWNS`, `HAS_*`, `BELONGS_TO`, `CONTAINS` → usually 1:N.
- Names ending in `_BY` (CREATED_BY, AUTHORED_BY) → usually N:1.
- Symmetric names like `KNOWS`, `FRIENDS_WITH`, `SHARES_*` → N:N.
- Activity verbs like `LIKED`, `RATED`, `VIEWED`, `PURCHASED` → N:N.
- Self-rels like `Customer-TRANSFERS_TO->Customer` → N:N, sparse fanout.
- For analytical use cases, transaction-style rels usually have higher
  fanout (100s to 1000s) than profile-style rels (single digits).

---

## Step 4: show a data preview

Before generating thousands of rows, show **5-10 sample rows per node
type and 3-5 per relationship type**, plus the total counts implied by
the cardinality table. The point is to catch "wait, that property
should be a UK postcode not a US zip" *before* a million rows of wrong
data.

Generate the sample on the fly inline — don't write the full script
yet. Use Faker directly in a small Python snippet (see
`scripts/build_script.py` for the property→generator logic; for
preview, just call the same generators).

Format:

> **Preview** at scale 10,000 (anchor=Customer):
>
> **Total counts:**
>
> | Label / Rel-type     | Count   |
> |----------------------|---------|
> | Customer             |  10,000 |
> | Account              |  25,000 |
> | Transaction          | 6,250,000 |
> | Device               |  13,000 |
> | OWNS                 |  25,000 |
> | PERFORMS             | 6,250,000 |
> | USES                 |  13,000 |
>
> **Customer sample (5 of 10,000):**
> ```
> customerId    name              email                       country
> CUST1000001   Ayesha Khan       ayesha.khan@example.com     GB
> CUST1000002   Marco Rossi       m.rossi@example.com         IT
> CUST1000003   Lina Park         lina.p@example.com          KR
> CUST1000004   Daniel Schmidt    d.schmidt@example.com       DE
> CUST1000005   Emma Wilson       emma.w@example.com          GB
> ```
>
> **Transaction sample (5 of 6.25M):**
> ```
> transactionId       amount    currency  type            date
> TXN000000000001     34.50     GBP       FASTER_PAYMENT  2026-04-12
> TXN000000000002     1450.00   EUR       SWIFT           2026-03-08
> ...
> ```

If the totals look unreasonable for the user's environment ("6 million
transactions on 10K customers feels high"), say so directly with the
fix:

> ⚠ Note: Transaction count is 6.25M, which will produce a ~600 MB
> CSV. If that's not what you wanted, adjust PERFORMS down — say
> "PERFORMS should be 50 per account" and I'll re-render.

Pause. The user can:

- **Accept** → proceed to Step 5.
- **Reject the values** ("emails should look like work emails, not
  example.com") → adjust the per-property generator and re-render the
  preview.
- **Reject the counts** → loop back to Step 3, edit cardinality,
  re-preview.

---

## Step 5: ask about patterns

Patterns are deliberate structures planted in the data so the user can
test detection logic. Each pattern adds extra nodes/edges on top of
the base data and is recorded in `injected_patterns.json` (ground
truth) so the user can measure detector recall.

Propose a menu of patterns **based on the use case from Step 2**, not
a generic list. Examples:

| Use case | Patterns to offer |
|---|---|
| Fraud detection | Cyclic transfer rings (A→B→C→A); shared-device clusters; high-fanout money mules; structuring (sub-threshold transaction bursts) |
| AML / structuring | Structuring bursts; round-trip transfers; rapid onboarding+drainage |
| Entity resolution | Shared identifiers (phone, address, email) with controlled overlap |
| Recommendation | Community structure (clusters of users with shared preferences) |
| Anomaly detection | Hub anomalies; off-hours activity bursts; geographic outliers |
| Generic test data | None by default — offer "no patterns" as the default |

Format the question:

> **Want any patterns planted?** Given fraud detection, the useful ones are:
>
>   • **Cyclic rings** — N customers transferring in a circle (3-5 hops).
>     Useful for testing ring-detection Cypher.
>   • **Shared-device clusters** — multiple customers using the same
>     device. Useful for fingerprint-based fraud queries.
>   • **High-fanout mules** — a few customers receiving from many.
>   • **Structuring bursts** — bursts of just-under-threshold transactions.
>   • **No patterns** — clean base data only.
>
> Pick any combination, or say "skip".

For each pattern the user chooses, ask a short follow-up about count
and parameters:

> Cyclic rings: how many, and how long?
>   • 50 rings of 3-5 customers each (recommended for 10K scale)
>   • Custom — tell me

**Validate against the schema before adding a pattern.** A cyclic ring
pattern needs a self-relationship on the participating label. If the
schema doesn't have one, tell the user honestly and skip that pattern:

> ⚠ Your schema has no `Customer -[*]-> Customer` relationship, so I
> can't plant cyclic rings. If you want them, you'll need to add a
> self-rel like `TRANSFERS_TO` to the schema first, or pick a
> different pattern.

---

## Step 6: write and run the script

Now build the script. Pass everything that's been collected to
`build_script.py` as a single JSON config:

```bash
cat > /home/claude/run_config.json <<EOF
{
  "anchor_label": "Customer",
  "anchor_count": 10000,
  "use_case": "fraud detection (rings + shared devices)",
  "schema_path": "/home/claude/graph_schema.json",
  "cardinality": {
    "OWNS":         {"from": "Customer", "to": "Account",     "kind": "1:N", "avg": 2.5},
    "PERFORMS":     {"from": "Account",  "to": "Transaction", "kind": "1:N", "avg": 250},
    "USES":         {"from": "Customer", "to": "Device",      "kind": "N:N", "avg": 1.3},
    "TRANSFERS_TO": {"from": "Customer", "to": "Customer",    "kind": "N:N", "avg": 5}
  },
  "property_generators": {
    "Customer.customerId":   {"type": "sequence", "prefix": "CUST", "start": 1000000},
    "Customer.name":         {"type": "faker",    "method": "name"},
    "Customer.country":      {"type": "categorical", "values": ["GB","US","DE","FR","IT","ES","KR","JP","SG","IN"]},
    "Transaction.amount":    {"type": "lognormal", "mu": 4.0, "sigma": 1.5, "min": 1.0, "max": 50000.0, "round_to": 2},
    "Transaction.currency":  {"type": "categorical", "values": ["GBP","USD","EUR"]}
  },
  "patterns": [
    {"type": "cyclic", "count": 50, "ring_size": [3, 5], "rel": "TRANSFERS_TO", "node": "Customer"},
    {"type": "shared_attr", "count": 100, "cluster_size": [5, 10], "hub": "Device", "member": "Customer", "rel": "USES"}
  ],
  "output_dir": "/home/claude/graph_data",
  "seed": 42
}
EOF

python3 /mnt/skills/user/graph-data-workflow/scripts/build_script.py \
    /home/claude/run_config.json \
    /home/claude/generate.py
```

`build_script.py` writes a **standalone** `generate.py` that:

- Has only `faker` as a dependency.
- Embeds the cardinality, generators, and patterns from the config so
  the user can re-run it later or edit it.
- Writes one CSV per label and per rel-type.
- Plants any patterns and emits `injected_patterns.json` as ground truth.
- Sets the random seed for reproducibility.

Then run it:

```bash
python3 -m venv /home/claude/venv 2>/dev/null
/home/claude/venv/bin/pip install faker -q
/home/claude/venv/bin/python3 /home/claude/generate.py
```

Copy outputs to `/mnt/user-data/outputs/`:

- `generate.py` (the standalone script the user can re-run)
- `run_config.json` (the config it was built from)
- All `nodes_*.csv` and `rels_*.csv` files
- `injected_patterns.json` if patterns were planted

Present the files via `present_files` with a short summary:

> Generated **<X> nodes / <Y> rels** across <Z> CSVs (~<size>).
> [<N> patterns planted; ground truth in `injected_patterns.json`.]
>
> The script `generate.py` is standalone — re-run it locally with
> `pip install faker && python generate.py` to regenerate or tweak.

---

## Rules that apply across all steps

- **One question at a time, with concrete options.** Use
  `ask_user_input_v0` for any step that asks the user to pick from a
  list. Never wall-of-text the user with five questions in one message.
- **Pause for confirmation.** Steps 1, 2, 3, 4, and 5 all end with a
  question. Don't proceed in the same turn as the question.
- **No silent assumptions.** If the user said "fraud detection" but
  hasn't specified scale, ask. If the user said "10K" but hasn't picked
  a use case, ask.
- **Edits go back into the config, not into hidden state.** The user
  should be able to see and re-run the exact same generation later.
- **The script Claude writes is standalone.** It should run on a
  laptop with `pip install faker` and nothing else.

## What's deliberately not here

- **No domain packs.** Claude reads the schema and reasons in
  conversation. Domain knowledge ("ATO event chains look like
  Authentication → ChangePhone → Transfer") comes from Claude
  understanding the labels, not from a JSON file.
- **No fingerprint scoring.** Step 2 proposes options based on
  reading the schema, not on weighted matches.
- **No spec contract.** The "config" is just whatever JSON
  `build_script.py` accepts at the moment — schema lives in the script,
  not in a separate JSON Schema file. Keep it simple.
- **No verification phase.** Once the data is generated, the user
  can run their own queries against it. If they want help running
  detection queries, that's a different conversation — not built into
  this skill.
