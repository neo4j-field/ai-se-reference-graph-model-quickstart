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

Generates fake graph data tuned to a specific use case. Produces CSVs ready
for Neo4j ingestion, plus optional planted patterns for analytical testing
(fraud detection, similarity matching, anomaly detection).

## When to Use

- User has a graph schema and wants test data populated against it
- User asks to generate fake/mock/synthetic/sample data for their graph
- User needs CSVs for Neo4j's LOAD CSV, Data Importer, or `neo4j-admin database import`
- User wants to test analytical queries (fraud rings, similarity, anomalies)
  against a realistic-looking dataset

## Prerequisites

The script needs Python 3.9+ and the `faker` library, installed inside a
virtual environment (see Step 6).

## How the workflow is structured

The skill works in two phases: **figure out what kind of dataset the user
needs**, then **generate it**. Most of the value is in the first phase —
asking the right questions about purpose so the data fits their use case.

```
Step 1   Get the schema
Step 2   Establish purpose                              ← anchor
            • Fingerprint the schema
            • Elicit & confirm the business question
            • ASK SCALE (explicit choice; recommendation + options)
Step 3   Configure data — bundled proposal              ← one round-trip
            (cardinality + identifiers + patterns,
             all derived from purpose; scale already picked)
Step 4   Preview & iterate                              ← MANDATORY PAUSE
            (dry-run, present numbers, wait for explicit "go ahead";
             never run generation in the same turn as the preview)
Step 5   Decide path (sandbox vs local handoff)
Step 6   Run base generation
Step 7   Inject patterns (if configured)
Step 8   Present results & next steps
```

The interaction style:
- **Scale is an explicit question** (Step 2.4) — users have strong opinions
  about volume, so don't hide it inside a bundle.
- Everything else is **recommend, then confirm**. Claude infers what's
  likely and proposes it as a bundle; the user accepts wholesale or
  adjusts specifics. Don't ask blank questions when reasonable defaults
  are available.
- The preview (Step 4) is the editable surface for fine-tuning; users
  iterate there with real numbers.

---

## Step 1: Get the Schema

The user provides their graph schema in one of three ways:

1. **Exported JSON from graph-schema-studio** — arrows.app-compatible,
   with `nodes` and `relationships` arrays. Save to `/home/claude/graph_schema.json`.
2. **Described in conversation** — "I have Customer, Account, Transaction
   nodes connected by OWNS and TRANSFERS_TO." Construct the JSON yourself.
3. **From the current conversation** — if they just used graph-schema-studio,
   reuse the schema they built.

Schema format:
```json
{
  "graph": {
    "nodes": [
      {"id": "n0", "caption": "Customer", "labels": ["Customer"],
       "properties": {"name": "string", "email": "string", "phone": "string"}}
    ],
    "relationships": [
      {"id": "r0", "type": "OWNS", "fromId": "n0", "toId": "n1",
       "properties": {"since": "date"}}
    ]
  }
}
```

---

## Step 2: Establish Purpose

This is the most important step. Everything downstream — scale, patterns,
identifiers — should follow from what the user is actually trying to do.

### Step 2.1 — Fingerprint the schema

Inspect the schema's node labels and look for known archetypes. Confidence
matters here — only **High** confidence schemas should get a confident
proposal. Hints should be presented as "could fit a few things, what are
you doing?" rather than as claims.

**High confidence — schema fingerprints uniquely:**

| Telltale labels                                                    | Likely use case                  |
|--------------------------------------------------------------------|----------------------------------|
| Customer, Account, Transaction, Device, Case + RelationshipManager | Fraud detection (banking)        |
| Patient, Provider, Claim, Diagnosis, Procedure                     | Healthcare claims fraud          |
| Patient + Diagnosis + Medication + Doctor                          | Clinical patient analytics       |
| Customer + Order + Product + Cart                                  | E-commerce analytics             |
| Customer + Order + Product + Review/Rating                         | Recommendation systems           |
| User + Post + Comment + Like + Follow                              | Social network analysis          |
| Author + Paper + Citation + Journal/Institution                    | Academic / citation network      |
| Component + Assembly + Part + Supplier                             | Supply chain / manufacturing     |
| Asset + Vulnerability + Threat + Identity                          | Cybersecurity (threat graph)     |

**Hint-only — has some signal but ambiguous; do NOT claim it:**

| Schema shape                                | Could be...                                                |
|---------------------------------------------|------------------------------------------------------------|
| Customer + Account + Transaction (alone)    | Banking analytics, fraud, telco billing, retail loyalty, subscription mgmt |
| User + Post (alone)                          | Social, blogging, CMS, knowledge base                       |
| Person + Person + KNOWS-type rel            | Social, contacts, org chart, citation                       |
| Movie + Person + ACTED_IN                   | Recommendation, generic demo, content cataloging            |
| Order + Customer + Product (no Review/Cart) | E-commerce, B2B sales, subscription                         |

**No confident match:**

| Schema shape          | Action               |
|-----------------------|----------------------|
| Anything else         | Ask open-ended       |

⚠️ **The fingerprint can be wrong.** A schema with `Customer + Account +
Transaction` could be banking, retail loyalty, telco, subscription, or
generic CRM — five different things from the same labels. Bias toward
asking when in doubt; the cost of a wrong claim ("this looks like
banking analytics...") is the user has to actively correct it before
any work proceeds. Don't make claims you can't back up from labels alone.

The fingerprint feeds **two** decisions: the **flavor** for Faker providers
(banking → finance flavor, patient → healthcare flavor) and the **likely use
case** for pattern suggestions.

### Step 2.2 — Confirm purpose with the user

Ask **one combined question** that elicits the business question, confirms
the flavor, and surfaces the use case archetype. Frame as a user story
when proposing — this naturally captures both the role and the analytical
target. The framing depends on fingerprint confidence:

**If fingerprint is High confidence:**

Make a confident proposal but include an off-ramp.

> Your schema looks like a fraud detection setup (Customer + Account +
> Transaction + Device + Case). The most common business question for
> this shape is:
>
> > *"As a fraud analyst, I want to find rings of customers transferring
> > money in cycles or sharing devices, so I can flag them for review."*
>
> Does that match? If you're doing something different — AML, query
> performance benchmarking, ingestion testing, or just exploring — tell me.

**If fingerprint is Hint-only (ambiguous):**

Don't claim a use case. Ask openly with the realistic possibilities.

> Your schema could fit several use cases. What are you trying to do?
>
>   • An analytical query — fraud detection, similarity matching,
>     recommendation, anomaly detection
>   • Performance / load testing (need volume; queries are arbitrary)
>   • Ingestion / pipeline testing (just need valid CSVs to load)
>   • Building a demo or prototype
>   • **Not sure yet — give me something flexible** (good for exploring)
>   • Other — tell me your business question

**If fingerprint matches nothing:**

Open-ended question with the same options.

> What are you trying to do with this data?
>
>   • An analytical query — fraud detection, similarity matching,
>     recommendation, anomaly detection
>   • Performance / load testing
>   • Ingestion / pipeline testing
>   • Building a demo or prototype
>   • Not sure yet — give me something flexible
>   • Other — tell me your business question
>
> A user-story-style answer is most useful ("as a [role] I want to [goal]
> so I can [reason]"), but anything works.

**The "Not sure yet" path is important.** Most data generation requests
are exploratory, not goal-driven. Users who pick this should get a
balanced, flexible default rather than being routed to a misfit
archetype. See `exploratory` in Step 2.3.

### Step 2.3 — Map use case to internal archetype

Internally, classify the user's confirmed answer into one of these archetypes.
This drives recommended defaults in Step 3.

⚠️ **Treat archetypes as templates, not classifications.** Many real
conversations don't fit cleanly into one bucket — a user might say "I'm
doing fraud detection but I need it at performance-test scale," meaning
they want fraud's patterns and identifier collisions but Large scale.
The archetype is the closest-matching starting point; mix and match
defaults when the user's actual need is between buckets. Never force a
user into the "wrong" archetype because none of the labels fit.

| Archetype           | Examples                                        | Implies                              |
|---------------------|-------------------------------------------------|--------------------------------------|
| `fraud_detection`   | "find fraud rings", "AML", "money laundering"   | patterns + identifier collisions     |
| `similarity`        | "entity resolution", "find duplicates", "match" | identifier collisions, shared_attr   |
| `anomaly_detection` | "find outliers", "flag unusual"                 | hub patterns + cyclic                |
| `recommendation`    | "collaborative filtering", "similar items"      | shared_attr clusters                 |
| `ingestion_test`    | "just need data", "load testing", "validate CSV"| no patterns, no identifier coll.     |
| `performance_test`  | "benchmark queries", "load test Neo4j"          | volume matters; patterns optional    |
| `demo_or_prototype` | "demo", "prototype", "presentation"             | small scale; patterns optional       |
| `exploratory`       | "not sure yet", "just exploring", "see what's possible" | medium scale, modest collisions, no patterns; broad enough to support various queries |
| `other_analytical`  | something analytical we don't recognize         | offer pattern menu, let user choose  |

The archetype is internal — the user doesn't need to see this label. It's
what Claude uses to pick recommended defaults in Step 3.

### Step 2.4 — Ask the user for scale

Scale is the one configuration choice users have strong opinions about,
and burying it in a bundled proposal feels like Claude decided for them.
Ask explicitly, with a recommendation tied to the archetype.

**Format:**

> How much data should I generate? Recommended: **Medium (10K)** for
> [reason tied to archetype]. Other options:
>
>   • **Small** (100) — quick demo or smoke test
>   • **Medium** (10K) — recommended ✓
>   • **Large** (1M) — performance / load testing
>   • **XL** (10M) — scale benchmarking (runs locally, not in sandbox)
>   • **Custom** — tell me a number

The recommended option depends on archetype (see table below), but
**always show all four standard tiers + Custom** so the user can override.
Don't hide options behind the recommendation.

**Recommendation by archetype:**

| Archetype             | Recommended | Reason for the recommendation                     |
|-----------------------|-------------|---------------------------------------------------|
| `demo_or_prototype`   | Small (100) | A handful of records is enough                    |
| `ingestion_test`      | Medium (10K)| Enough to exercise CSV import paths               |
| `fraud_detection`     | Medium (10K)| Rings are findable at this scale; fast iteration  |
| `similarity`          | Medium (10K)| Similarity algorithms work at any scale           |
| `recommendation`      | Medium (10K)| Cold-start works at modest scale                  |
| `anomaly_detection`   | Medium (10K)| Anomalies are visible at this scale               |
| `performance_test`    | Large (1M)  | Performance work needs realistic volumes          |
| `exploratory`         | Medium (10K)| Flexible default; supports many query types       |
| `other_analytical`    | Medium (10K)| Safe default                                      |

**Scale tiers and where they run:**

| Tier    | Anchor count | Where it runs            |
|---------|--------------|--------------------------|
| Small   | 100          | Sandbox (foreground)     |
| Medium  | 10,000       | Sandbox (foreground)     |
| Large   | 1,000,000    | Sandbox (background+poll)|
| XL      | 10,000,000   | Local handoff (script)   |

If the user picks Custom, ask for the number. Validate it's a positive
integer; route automatically to sandbox-vs-handoff based on the threshold
(see Step 5).

**Stop and wait for the user's answer.** Don't proceed to Step 3 until
the scale is confirmed. This is a real elicitation, not a recommendation
the user passively accepts.

---

## Step 3: Configure Data (Bundled Proposal)

Step 3 is **one round-trip**. The user already chose scale in Step 2.4,
so the bundle covers cardinality + identifier collisions + patterns,
all derived from schema + archetype. Present as a single proposal the
user can accept wholesale or adjust piecemeal.

The reference tables that follow are inputs Claude uses to construct the
bundle — they are not separate elicitations.

### Reference: Cardinality inference

Auto-classify each relationship by name pattern:

| Pattern (rel-type name)                                  | Cardinality | Confidence |
|----------------------------------------------------------|-------------|------------|
| `OWNS`, `BELONGS_TO`, `PART_OF`, `CONTAINS`              | 1:N or N:1  | High       |
| `INITIATED_BY`, `CREATED_BY`, `AUTHORED_BY`, `*_BY`      | N:1         | High       |
| `SHARES_*`, `KNOWS`, `FRIENDS_WITH`, `FOLLOWS`           | N:N         | High       |
| `ACTED_IN`, `RATED`, `LIKED`, `VIEWED`, `PURCHASED`      | N:N         | High       |
| `HAS_<singular>` (HAS_PHONE, HAS_ADDRESS)                | 1:N         | Medium     |
| `HAS_<plural>` (HAS_TAGS, HAS_LABELS)                    | N:N         | Medium     |
| `MANAGES`, `REPORTS_TO`, `SUPERVISES`                    | 1:N or N:1  | Low ⚠️     |
| `USES_*`, `WORKS_AT`, `LIVES_AT`, `LOCATED_AT`           | varies      | Low ⚠️     |
| `INVOLVED_IN`, `RELATED_TO`, `ASSOCIATED_WITH`           | N:N         | Medium     |
| Anything else                                            | N:N         | Default    |

Flag low-confidence (⚠️) ones in the bundle so the user knows where to
look. For "1:N or N:1" entries, pick from schema direction:
- **A → B** with name implying "B belongs to A" → **1:N**
  (e.g. `Author-WROTE-Book`, `Customer-OWNS-Account`)
- Implying "A belongs to B" → **N:1**
  (e.g. `Order-PLACED_BY-Customer`)

### Reference: Identifier collisions (analytical archetypes only)

Skip for `ingestion_test`, `performance_test`, `demo_or_prototype`.
Include for `fraud_detection`, `similarity`, `recommendation`,
`anomaly_detection`, `other_analytical`. For `exploratory`, include
modest defaults.

Scan node properties for identifier-shaped names:

| Property name (case-insensitive)                          | Identifier? |
|-----------------------------------------------------------|-------------|
| `phone`, `phone_number`, `mobile`, `whatsapp`             | yes         |
| `email`                                                   | yes (rare)  |
| `ssn`, `tax_id`, `passport`, `nric`, `national_id`        | yes         |
| `account_number`, `iban`, `routing_number`, `card_number` | yes         |
| `ip_address`, `ipv4`, `mac_address`, `device_id`, `imei`  | yes         |
| `username`, `handle`, `screen_name`                       | yes         |
| `address`, `street_address`, `postal_code`                | yes (rarer) |
| `name`, `description`, `notes`, `bio`, `category`,
  `status`, `title`, `tag`                                  | NO          |

Defaults:

| Identifier        | Share % | Cluster size | Why                          |
|-------------------|---------|--------------|------------------------------|
| phone, mobile     | 10%     | 3-5          | family plans                 |
| ip_address        | 5%      | 5-15         | NAT, shared WiFi             |
| address           | 3%      | 2-3          | households                   |
| ssn, national_id  | 0.5%    | 2            | data errors only             |
| account_number    | 1%      | 2-3          | joint accounts               |
| device_id, imei   | 2%      | 2-3          | resold devices               |
| username          | 1%      | 2            | typos                        |

### Reference: Analytical patterns (analytical archetypes only)

Skip for `ingestion_test`, `performance_test`, `demo_or_prototype`,
`exploratory` (unless user asks). Include for analytical archetypes.

| Archetype           | Suggested patterns                                |
|---------------------|---------------------------------------------------|
| `fraud_detection`   | `cyclic` (rings) + `shared_attr` (shared IDs)     |
| `similarity`        | `shared_attr` (mainly via identifier collisions)  |
| `recommendation`    | `shared_attr` (community structure)               |
| `anomaly_detection` | `hub` (high fan-out) + `cyclic`                   |
| `other_analytical`  | offer the menu, let user pick                     |

⚠️ **Patterns are detectable, not adversarial.** They're constructed to be
findable by simple Cypher queries — useful for prototyping detection logic
and measuring recall, but not a substitute for testing detectors against
real-world adversarial data. Be honest about this in the bundle if the
archetype is fraud-adjacent.

#### Pattern catalog

**1. `cyclic` — cyclical chains.** A→B→C→...→A. Money laundering rings,
citation cabals, circular ownership. Needs a **self-relationship** on the
participating node label. Spec:
`cyclic:<count>:<min-max>:rel=<REL>,node=<Label>`
Example: `cyclic:50:3-5:rel=TRANSFERS_TO,node=Customer`

**2. `shared_attr` — shared-attribute clusters.** N entities all linked to
one shared neighbor. Fraud rings via shared devices, similar customers,
duplicate identities. Needs a rel between two distinct labels. Spec:
`shared_attr:<count>:<min-max>:hub=<Label>,member=<Label>,rel=<REL>`
Example: `shared_attr:100:5-10:hub=Device,member=Customer,rel=USES_DEVICE`

**3. `hub` — hub anomalies.** A single node with abnormally high
out-degree. Money mules, super-spreaders, citation authorities. Spec:
`hub:<count>:fanout=<N>,rel=<REL>`
Example: `hub:5:fanout=200,rel=TRANSFERS_TO`

#### Schema validation before including a pattern

- `cyclic` requires a self-rel (`fromId == toId`) on the right label.
  If absent, drop the pattern from the bundle and tell the user why
  ("your schema has no self-rel on Customer, so cyclic rings can't be
  planted; falling back to shared_attr only").
- `shared_attr` requires a rel between the proposed hub and member labels.
- `hub` works on any rel; pick one with high-cardinality target side.

#### How many patterns to plant

⚠️ **Don't anchor on specific numbers — reason from a principle.** Plant
enough patterns that detection has a non-trivial signal-to-noise ratio,
but not so many that planted structures dominate the data.

A practical default: **roughly 0.5–1% of the base node count** for cyclic
and shared_attr patterns; **5–20 hubs total** regardless of scale (hubs
are inherently rare). For example:

- 1,000 nodes → ~5–10 cyclic rings, ~10 shared-attr clusters, 2–5 hubs
- 10,000 nodes → ~50 rings, ~100 clusters, 5 hubs
- 1,000,000 nodes → ~500–1000 rings, ~1000 clusters, 10–20 hubs

Cluster sizes / ring lengths / hub fanouts: catalog defaults are usually
fine (3-5 hop rings, 5-10 member clusters, ~200 fanout). Adjust if the
schema has unusual structure that makes these wrong.

If the user pushes back on counts in the preview, that's the place to
tune — not here.

### The bundled proposal

Compose all of the above into a single message. Use a structured but
conversational format. The scale is already known (the user picked it
in Step 2.4), so the bundle **acknowledges** their choice and then
proposes the rest.

Example for a `fraud_detection` archetype where the user picked Medium:

> Got it — Medium (10K) for fraud detection. Here's the rest of what
> I'm proposing:
>
> **Cardinality** (auto-inferred from rel names):
>   1:N   OWNS              Customer → Account
>   N:N   USES_DEVICE       Customer ↔ Device       ⚠️ low confidence
>   N:N   SHARES_DEVICE     Customer ↔ Customer
>   1:N   MANAGES           RelationshipManager → Customer  ⚠️ low confidence
>   N:N   TRANSFERS_TO      Customer ↔ Customer
>
> **Realistic identifier overlap** (so similarity / fraud queries find
> something):
>   • `phone` on Customer    — 10% shared, clusters of 3-5
>   • `device_id` on Device  — 2% shared, clusters of 2-3
>
> **Analytical patterns to plant** (recorded in `injected_patterns.json`
> as ground truth):
>   • ~50 cyclical TRANSFERS_TO rings (3-5 customers per ring)
>   • ~100 shared-device clusters (5-10 customers per Device hub)
>   • ~5 hub anomalies (each transferring to ~200 customers)
>
> Note: these patterns are designed to be detectable by straightforward
> Cypher queries. Useful for prototyping detection and measuring recall,
> not for adversarial validation.
>
> **Accept all this**, or tell me what to change — e.g., "skip patterns,"
> "MANAGES should be N:1 not 1:N," "no shared phones." (Scale is locked
> in from your earlier answer; if you want to change scale, say so and
> I'll re-do the bundle.)

For non-analytical archetypes (`ingestion_test`, `performance_test`,
`demo_or_prototype`), the bundle is shorter — no identifier or pattern
sections — and the framing is more about volume and cardinality.

For `exploratory`, include modest identifier collisions but no patterns;
note that patterns can be added later by re-running.

#### Handling pushback

The user might:
- **Accept all** → proceed to Step 4 with these settings
- **Adjust one piece** ("skip patterns") → update the bundle, re-present
- **Adjust multiple pieces** → update all in one go, re-present once
- **Want to see numbers first** → proceed to Step 4 (preview shows actual
  counts; the bundle is the *plan*, the preview is the *outcome*)

Don't loop on the bundle indefinitely — if the user has made 2-3
adjustments, move to the preview and let them iterate there with real
numbers. The preview is the editable surface for fine-tuning; the
bundle is for getting roughly the right shape.

---

## Step 4: Preview & Iterate

**This step has a mandatory pause.** Run the dry-run, present the
preview, then **stop and wait for the user's explicit confirmation
before any generation runs**. The preview is the user's last off-ramp
before a long-running operation; skipping the pause turns it into a
fancy progress message rather than a decision surface.

### The pause is non-negotiable

After presenting the preview, Claude must:

1. **End the turn.** Do not run generation in the same turn as the preview.
   The preview message is the *last* thing Claude says in that turn. No
   "kicking it off now" sentences, no immediate bash calls.

2. **Wait for explicit confirmation.** Acceptable confirmations:
   - "yes" / "ok" / "go ahead" / "proceed" / "looks good" / "do it"
   - "kick it off" / "run it" / "generate" / "start"
   - Any clear affirmative reply

   **Not** acceptable as confirmation:
   - Silence (the user simply not responding)
   - A question ("how long will it take?")
   - A statement of preference without instruction ("I think Medium is fine")
   - A clarification request ("what's a hub anomaly?")
   - Any pushback or adjustment request

3. **Treat anything that isn't an explicit confirmation as either an
   adjustment to make or a question to answer.** Loop back to the bundle
   or preview as appropriate. Don't infer consent from neutrality.

This applies to **all scales**, including small ones. Even at Small (100),
the user should get the chance to say "actually I want fraud patterns
too" before generation runs. The pause is cheap; an unwanted run is not.

### Run dry-run

```bash
/home/claude/graph_venv/bin/python3 /home/claude/generate_data.py \
  /home/claude/graph_schema.json \
  --output-dir /tmp/dryrun-discard \
  --scale <SCALE> \
  --flavor <FLAVOR> \
  --cardinality "<...>"  \
  --node-counts "<...>"   \
  --rel-fanout "<...>"    \
  --rel-counts "<...>"    \
  --shared-identifiers "<...>"  \
  --dry-run
```

The script emits JSON to stdout (no files written).

### Present the preview

Parse the JSON and present a structured preview. The closing line **must
be an explicit ask for confirmation, framed as a stop, not a continue**.

> Here's what I'll generate for [use case description]:
>
> **Nodes** (X total):
>   Customer            10,000
>   Account              2,000
>   Transaction          5,000
>   Device               1,000
>
> **Relationships** (Y total):
>   Customer -[OWNS 1:N]-> Account             2,000
>   Customer -[USES_DEVICE N:N]-> Device      20,000
>   Customer -[TRANSFERS_TO N:N]-> Customer   30,000
>
> **Realistic identifier overlap:**
>   phone: 10% shared in clusters of 3-5  (~1,000 customers in ~250 clusters)
>
> **Analytical patterns to be injected (after generation):**
>   50 cyclical TRANSFERS_TO rings (3-5 customers each)
>   100 shared-device clusters (5-10 customers per Device)
>   5 high-fanout hub customers (200 transfers each)
>
> **Estimated:** ~50 MB of CSVs, ~30 seconds runtime.
>
> ⏸ **I'm pausing here for your confirmation before generating anything.**
> Reply "go ahead" to start, or tell me what you'd like to change
> (scale, cardinality, identifiers, patterns, anything).

The ⏸ pause indicator and the explicit "before generating anything" make
the stop visible. Don't skip these even if the previous conversation has
been smooth — the user might want to add or remove something they hadn't
mentioned.

### The preview is the editable surface

When users push back, **translate their words into flags and re-run
dry-run**. Don't restart the whole flow, don't modify the script.

| User says... | Flag to use | Example |
|---|---|---|
| "Only N Customers" | `--node-counts Label=N` | `Customer=200000` |
| "Each X has 2-3 Y" | `--rel-fanout REL=ratio` | `OWNS_TX=2.5` |
| "Cap REL at N" / "At most N" | `--rel-counts REL=N` | `USES_DEVICE=500000` |
| "Smaller graph" | reduce `--scale` | `--scale 100000` |
| "Sparser N:N" | reduce `--nn-fanout` | `--nn-fanout 1.2` |
| "Just a few of these" | low absolute via `--node-counts` | `Case=1000` |
| "More fraud rings" | adjust pattern count | `cyclic:200:3-5:...` |
| "Different identifier overlap" | adjust `--shared-identifiers` | `phone:5%:2-3` |

After applying any adjustment, **re-run dry-run and present the updated
preview**. Then pause again. Each iteration is a fresh pause; don't
collapse multiple changes into a silent re-run.

If the request is genuinely outside the flags' expressive power (e.g.,
"exactly 17 Transactions per Customer with Gaussian distribution"), say
so honestly. Don't patch the script.

Loop until the user gives explicit confirmation. Only then proceed to
Step 5.

---

## Step 5: Decide the Path — Sandbox or Local Handoff

**Threshold: 2,000,000 anchor nodes.**

- `scale ≤ 2,000,000` → **sandbox path**. Run in this environment.
  - For `scale ≥ 500,000`, launch the generator **in the background** and
    poll for completion (single foreground bash calls hit per-command
    timeouts at ~2 min).
- `scale > 2,000,000` → **local handoff**. Don't run here. Package
  `generate_data.py` + `inject_patterns.py` + `README.md` + `schema.json`
  for the user to run locally.

In-sandbox generation is reliable up to about 1M anchor nodes (~5 min wall
time for a multi-node-type schema). 2M leaves a buffer; above that, runtimes
get long enough that local execution is cleaner.

---

## Step 6: Run Base Generation

### Set up the venv

```bash
if [ ! -d "/home/claude/graph_venv" ]; then
    python3 -m venv /home/claude/graph_venv
fi
/home/claude/graph_venv/bin/pip install faker -q
```

Use the venv interpreter directly (no need to `source activate`).

### Foreground execution (scale < 500,000)

```bash
cp "$SKILL_DIR/assets/generate_data.py" /home/claude/generate_data.py
/home/claude/graph_venv/bin/python3 /home/claude/generate_data.py \
  /home/claude/graph_schema.json \
  --output-dir /home/claude/graph_data \
  --scale <ANCHOR_COUNT> \
  --flavor <FLAVOR> \
  --cardinality "<REL>=<CARD>,..." \
  --node-counts "<Label>=<N>,..." \
  --rel-fanout "<REL>=<MULT>,..." \
  --rel-counts "<REL>=<N>,..." \
  --shared-identifiers "<P>:<%>:<min-max>,..."
```

**Always pass the same flags that produced the accepted preview.** The
dry-run from Step 4 is the source of truth.

### Background execution with polling (scale ≥ 500,000)

```bash
cp "$SKILL_DIR/assets/generate_data.py" /home/claude/generate_data.py
/home/claude/graph_venv/bin/python3 /home/claude/generate_data.py \
  /home/claude/graph_schema.json \
  --output-dir /home/claude/graph_data \
  --scale <ANCHOR_COUNT> \
  --flavor <FLAVOR> \
  --cardinality "<REL>=<CARD>,..." \
  --node-counts "<Label>=<N>,..." \
  --rel-fanout "<REL>=<MULT>,..." \
  --rel-counts "<REL>=<N>,..." \
  --shared-identifiers "<P>:<%>:<min-max>,..." \
  2>/home/claude/gen.log &
echo "PID=$!"
```

Then poll in separate short bash calls every 30-60s:

```bash
tail -5 /home/claude/gen.log
ps -p <PID> > /dev/null 2>&1 && echo "running" || echo "done"
```

Relay meaningful progress to the user. Only proceed to Step 7 after the
process has exited successfully.

### Local handoff path (scale > 2,000,000)

Copy these to `/mnt/user-data/outputs/graph_data_generator/`:
- `generate_data.py` (from skill assets)
- `inject_patterns.py` (from skill assets, only if patterns configured)
- `README.md` (from skill assets)
- `schema.json` (the user's input schema)

Tell the user the install + run sequence:

> ```bash
> python3 -m venv venv && source venv/bin/activate
> pip install faker
> python generate_data.py schema.json --output-dir ./graph_data \
>   --scale <SCALE> [other flags...]
> # then if you configured patterns:
> python inject_patterns.py ./graph_data --pattern "..."
> ```

For XL (10M), recommend `neo4j-admin database import` over LOAD CSV — it's
an order of magnitude faster for bulk loads.

---

## Step 7: Inject Patterns (if configured)

Only fires if Step 3.4 configured at least one pattern. Run after base
generation has completed.

```bash
/home/claude/graph_venv/bin/python3 "$SKILL_DIR/assets/inject_patterns.py" \
  /home/claude/graph_data \
  --pattern "<spec1>" \
  --pattern "<spec2>" \
  --pattern "<spec3>"
```

Pass one `--pattern` flag per pattern type. **Pass them all in a single
invocation** — `injected_patterns.json` is rewritten on each run, not
appended (a known v1 limitation).

The script writes `injected_patterns.json` to the data directory:
ground-truth manifest of every planted pattern, with the exact node IDs
and edges. This is critical — without it, the user can't measure detector
recall against the planted truth.

---

## Step 8: Present Results & Next Steps

### Sandbox path output

Copy to `/mnt/user-data/outputs/graph_data/`:
- All `nodes_*.csv` and `rels_*.csv` files
- `schema.json`
- `injected_patterns.json` (if patterns were injected)
- `generate_data.py` (bonus — for local re-runs)
- `inject_patterns.py` (if patterns were used)
- `README.md`

Present a summary:

> Generated [X] nodes and [Y] relationships across [Z] CSV files (~[size]).
> [If patterns:] Injected [N] analytical patterns; see
> `injected_patterns.json` for ground-truth IDs.
>
> The script bundle is included in case you want to re-generate locally
> with different seeds or larger scale.

### Next-step options

For analytical archetypes, mention how to use the planted patterns:

> To verify the planted patterns are findable, try a Cypher query like:
>   `MATCH path = (c:Customer)-[:TRANSFERS_TO*3..5]->(c) RETURN path LIMIT 10`
> (this should match planted cyclic rings).
>
> Compare your detector's output to `injected_patterns.json` to measure
> recall.

Always offer:
- **Ingestion**: "Want me to ingest into your Neo4j (via MCP), or generate
  a standalone ingestion script?" (See `graph-neo4j-ingestion` skill.)
- **Re-run**: "Want to adjust scale, patterns, or seed and regenerate?"
- **Preview**: "Want to see a sample of the data before ingesting?"

For the **handoff path**, the user runs everything locally — offer to
generate the ingestion script as part of the bundle so they have both
tools ready before they start.

---

## Property Name Intelligence

The generator uses smart matching to produce realistic data based on
property names. Domain-specific generators activate from `(label, property)`
pairs — e.g., `Patient.name` produces patient names, `Drug.name` produces
drug names. The `--flavor` flag sets the Faker locale; the `(label, property)`
context generators handle domain dispatch regardless.

| Property | Generic | Healthcare | Finance | E-commerce |
|---|---|---|---|---|
| name | "John Smith" | "Dr. Priya Patel, MD" | "John Smith" | "John Smith" |
| email | "user1@example.com" (counter) | same | same | same |
| price, cost, total | 49.99 | — | 49.99 (USD) | 49.99 |
| amount, balance | 49.99 | — | 1,234.56 | — |
| iban, swift | — | — | valid-format | — |
| diagnosis, condition | — | "Type 2 Diabetes" | — | — |
| medication, drug | — | "Metformin 500mg" | — | — |
| icd10 | — | "E11.9" | — | — |
| sku, productCode | — | — | — | "SKU-48291" |
| status | "active" | "admitted" | "pending" | "shipped" |
| *Id (customerId, etc.) | UUID | UUID | UUID | UUID |

For unrecognized property names, falls back to declared type.

---

## Important Notes

- **Use case anchors everything.** Every later configuration (scale,
  identifiers, patterns) takes its lead from the use case established in
  Step 2. If the user pivots mid-conversation ("actually, I'm not doing
  fraud, I'm doing recommendation"), re-run Step 3 defaults rather than
  patching what's already there.
- **The 2M sandbox threshold.** Up to 2M anchor nodes, Claude generates
  in the sandbox. Between 500K and 2M the generator must be launched in
  the background with progress polling. Above 2M, package the script for
  local execution.
- **Scripts are pure Python with one dep (`faker`).** No toolchain beyond
  `pip install faker` is required for local runs.
- The generator is **deterministic** with a fixed seed by default. Same
  schema + scale + flags + seed → identical output. Pass `--seed <int>`
  to change.
- **Filenames preserve case** — `nodes_Customer.csv`, `rels_TRANSFERS_TO.csv`
  — so Neo4j labels and rel-types come out correctly.
- **Counter-based emails** (`user1@example.com`, `user2@example.com`, ...)
  by design. Faker's `unique.email()` has quadratic memoization cost at
  scale; the counter form is unique by construction, O(1), and keeps
  memory flat. Trade-off: emails look obviously synthetic. If you need
  Faker-style emails at small scale, edit `_unique_email` in the script.
- **Power-law fanout** for N:N relationships by default — realistic
  (a few super-connected nodes, many sparse ones). `--distribution uniform`
  for controlled tests.
- **`injected_patterns.json` is rewritten per run, not appended.** Run all
  pattern injections in one `inject_patterns.py` invocation to keep them
  in one manifest.
- **Schema-studio integration is partial.** The data generator reads
  schemas from graph-schema-studio's export format, but cardinality is
  not yet propagated through the export — Claude infers it here. If the
  schema-studio export later carries cardinality, this skill will use it.
