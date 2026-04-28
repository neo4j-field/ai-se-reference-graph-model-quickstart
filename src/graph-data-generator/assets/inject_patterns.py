#!/usr/bin/env python3
"""
Pattern Injection — adds analytical patterns (cyclical chains, shared-attribute
clusters, hub anomalies) on top of CSVs produced by generate_data.py.

Why this exists separately from generate_data.py:
  - Different concern: base generation produces plausible volumes; this
    injects structures designed to be detectable by analytical queries.
  - Different lifecycle: users iterate on patterns (try a few rings, see if
    queries find them, adjust) much more than they iterate on base data.
  - Different inputs: this works on any CSVs in the expected layout — could
    be applied to real data, partially-generated data, or sample data, not
    just generate_data.py output.

Usage:
    python inject_patterns.py <data_dir> \\
        --pattern cyclic:50:3-5:rel=TRANSFERS_TO,node=Customer \\
        --pattern shared_attr:100:5-10:via=Device \\
        --pattern hub:5:fanout=200:rel=USES_DEVICE

Each --pattern is a colon-separated spec:
    pattern_name : count : params

The data directory must contain `schema.json` (so we know what node types
and rel types exist) plus the relevant `nodes_<Label>.csv` and
`rels_<REL>.csv` files.

Output:
  - Modified CSV files (rows appended; existing rows untouched)
  - injected_patterns.json: ground-truth manifest of every planted pattern
    (which nodes participated, which edges were added, what the pattern
    looks like). Critical for evaluation — without this, you can't measure
    detector recall.
"""

import argparse
import csv
import json
import os
import random
import sys
import uuid
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers — schema/CSV reading
# ═══════════════════════════════════════════════════════════════════════════════

def load_schema(data_dir):
    schema_path = os.path.join(data_dir, "schema.json")
    if not os.path.exists(schema_path):
        print(f"ERROR: {schema_path} not found. The data directory must contain "
              f"the schema.json that generate_data.py wrote alongside the CSVs.",
              file=sys.stderr)
        sys.exit(1)
    with open(schema_path) as f:
        raw = json.load(f)
    return raw.get("graph", raw)


def find_node_files(data_dir, label):
    """Return all node CSVs for a label (handles chunked files)."""
    out = []
    for fn in sorted(os.listdir(data_dir)):
        # Match nodes_<Label>.csv and nodes_<Label>_partN.csv exactly
        if not fn.startswith(f"nodes_{label}"):
            continue
        # Avoid false-positives where Label is a prefix of another label
        rest = fn[len(f"nodes_{label}"):]
        if rest == ".csv" or (rest.startswith("_part") and rest.endswith(".csv")):
            out.append(os.path.join(data_dir, fn))
    return out


def find_rel_files(data_dir, rel_type):
    """Return all relationship CSVs for a rel-type (handles chunked files)."""
    out = []
    for fn in sorted(os.listdir(data_dir)):
        if not fn.startswith(f"rels_{rel_type}"):
            continue
        rest = fn[len(f"rels_{rel_type}"):]
        if rest == ".csv" or (rest.startswith("_part") and rest.endswith(".csv")):
            out.append(os.path.join(data_dir, fn))
    return out


def sample_node_ids(data_dir, label, k, rng):
    """
    Sample k node IDs of the given label. Reads through node CSVs without
    holding everything in memory by using reservoir sampling for large files.
    """
    files = find_node_files(data_dir, label)
    if not files:
        return []

    # Reservoir sampling across all files
    reservoir = []
    seen = 0
    for path in files:
        with open(path, newline="") as f:
            r = csv.reader(f)
            next(r, None)  # skip header
            for row in r:
                if not row:
                    continue
                node_id = row[0]
                if len(reservoir) < k:
                    reservoir.append(node_id)
                else:
                    j = rng.randrange(seen + 1)
                    if j < k:
                        reservoir[j] = node_id
                seen += 1
    return reservoir


def get_rel_property_columns(data_dir, rel_type):
    """Read the header of the first matching rel CSV to learn the property columns."""
    files = find_rel_files(data_dir, rel_type)
    if not files:
        return []
    with open(files[0], newline="") as f:
        header = next(csv.reader(f), [])
    # First two columns are _from_id, _to_id; rest are properties
    return header[2:]


def get_rel_endpoints(schema, rel_type):
    """Find from_label and to_label for a given rel type from the schema."""
    nodes = {n["id"]: (n["labels"][0] if n.get("labels") else n.get("caption", n["id"]))
             for n in schema.get("nodes", [])}
    for r in schema.get("relationships", []):
        if r.get("type") == rel_type:
            return nodes.get(r["fromId"]), nodes.get(r["toId"])
    return None, None


def append_rel_rows(data_dir, rel_type, rows, prop_columns):
    """
    Append rows to the relationship's CSV file. If the rel is chunked, we
    append to the LAST part (most recently written). For simplicity we
    don't try to balance across chunks — this is injection, low volume.
    """
    files = find_rel_files(data_dir, rel_type)
    if not files:
        # New rel type for this dataset; create a fresh file
        path = os.path.join(data_dir, f"rels_{rel_type}.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["_from_id", "_to_id"] + prop_columns)
            for row in rows:
                w.writerow(row)
        return path

    # Append to last existing file
    target = files[-1]
    with open(target, "a", newline="") as f:
        w = csv.writer(f)
        for row in rows:
            w.writerow(row)
    return target


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern: Cyclical Chains (A → B → C → A)
# ═══════════════════════════════════════════════════════════════════════════════

def inject_cyclic(schema, data_dir, count, length_range, rel_type, node_label, rng):
    """
    Plant `count` cyclical chains. Each chain is `length` nodes long
    (uniformly random in length_range), forming a cycle: n0→n1→n2→...→n0.
    Uses the specified rel_type, which must be a self-rel on the node_label
    (e.g. Customer-TRANSFERS_TO-Customer for money-flow rings).

    Returns: list of pattern records describing each planted ring.
    """
    from_label, to_label = get_rel_endpoints(schema, rel_type)
    if from_label != node_label or to_label != node_label:
        print(f"ERROR: cyclic pattern needs a self-relationship "
              f"({node_label}→{node_label}), but {rel_type} goes "
              f"{from_label}→{to_label}", file=sys.stderr)
        sys.exit(1)

    # Pre-sample enough node IDs for all rings
    max_len = length_range[1]
    needed = count * max_len
    pool = sample_node_ids(data_dir, node_label, needed, rng)
    if len(pool) < count * length_range[0]:
        print(f"ERROR: not enough {node_label} nodes ({len(pool)} sampled) "
              f"for {count} rings of size {length_range[0]}+", file=sys.stderr)
        sys.exit(1)

    prop_columns = get_rel_property_columns(data_dir, rel_type)

    new_rows = []
    patterns = []
    used = 0
    for ring_idx in range(count):
        ring_len = rng.randint(length_range[0], length_range[1])
        if used + ring_len > len(pool):
            print(f"WARN: ran out of nodes after {ring_idx} rings", file=sys.stderr)
            break
        ring_nodes = pool[used:used + ring_len]
        used += ring_len

        # Add edges forming the cycle: n0→n1, n1→n2, ..., n[len-1]→n0
        ring_edges = []
        for i in range(ring_len):
            from_id = ring_nodes[i]
            to_id = ring_nodes[(i + 1) % ring_len]
            # Use placeholder property values — they're synthetic anyway.
            row = [from_id, to_id] + ["" for _ in prop_columns]
            new_rows.append(row)
            ring_edges.append([from_id, to_id])

        patterns.append({
            "pattern": "cyclic",
            "ring_id": f"ring_{ring_idx:06d}",
            "length": ring_len,
            "node_label": node_label,
            "rel_type": rel_type,
            "node_ids": ring_nodes,
            "edges": ring_edges,
        })

    target_file = append_rel_rows(data_dir, rel_type, new_rows, prop_columns)
    return patterns, len(new_rows), target_file


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern: Shared Attribute Clusters
# ═══════════════════════════════════════════════════════════════════════════════

def inject_shared_attr(schema, data_dir, count, cluster_size_range,
                       rel_type, hub_label, member_label, rng):
    """
    Plant `count` shared-attribute clusters. Each cluster: K member-nodes
    all connected to 1 hub-node via rel_type. (E.g. 5 Customers all using
    the same Device.) Designed to be discoverable by "find sets of nodes
    sharing a common neighbor" queries.

    rel_type endpoint check: we need rel_type from member_label to hub_label
    (e.g. Customer-USES_DEVICE-Device).
    """
    from_label, to_label = get_rel_endpoints(schema, rel_type)
    # We accept either direction — the user's schema dictates it
    if {from_label, to_label} != {member_label, hub_label}:
        print(f"ERROR: shared_attr pattern needs {rel_type} between "
              f"{member_label} and {hub_label}, but it goes "
              f"{from_label}→{to_label}", file=sys.stderr)
        sys.exit(1)

    # Direction matters for writing edges
    member_is_from = (from_label == member_label)

    # Sample one hub per cluster, members per cluster
    hubs = sample_node_ids(data_dir, hub_label, count, rng)
    if len(hubs) < count:
        print(f"WARN: only {len(hubs)} {hub_label} nodes available, "
              f"reducing cluster count from {count}", file=sys.stderr)
        count = len(hubs)

    max_size = cluster_size_range[1]
    members_needed = count * max_size
    member_pool = sample_node_ids(data_dir, member_label, members_needed, rng)

    prop_columns = get_rel_property_columns(data_dir, rel_type)

    new_rows = []
    patterns = []
    used = 0
    for cluster_idx in range(count):
        size = rng.randint(cluster_size_range[0], cluster_size_range[1])
        if used + size > len(member_pool):
            print(f"WARN: ran out of {member_label} nodes after "
                  f"{cluster_idx} clusters", file=sys.stderr)
            break
        members = member_pool[used:used + size]
        used += size
        hub = hubs[cluster_idx]

        cluster_edges = []
        for member in members:
            if member_is_from:
                row = [member, hub] + ["" for _ in prop_columns]
            else:
                row = [hub, member] + ["" for _ in prop_columns]
            new_rows.append(row)
            cluster_edges.append([row[0], row[1]])

        patterns.append({
            "pattern": "shared_attr",
            "cluster_id": f"cluster_{cluster_idx:06d}",
            "hub_id": hub,
            "hub_label": hub_label,
            "member_ids": members,
            "member_label": member_label,
            "rel_type": rel_type,
            "edges": cluster_edges,
        })

    target_file = append_rel_rows(data_dir, rel_type, new_rows, prop_columns)
    return patterns, len(new_rows), target_file


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern: Hub Anomalies (super-connected nodes)
# ═══════════════════════════════════════════════════════════════════════════════

def inject_hub(schema, data_dir, count, fanout, rel_type, rng):
    """
    Plant `count` hub anomalies. Each hub is a single node that gets
    `fanout` outgoing edges of rel_type to other nodes. Detects "find
    nodes with abnormally high out-degree" queries — money mules, super-
    spreaders, citation cabals' central authors, etc.
    """
    from_label, to_label = get_rel_endpoints(schema, rel_type)
    if not from_label or not to_label:
        print(f"ERROR: rel_type {rel_type} not found in schema", file=sys.stderr)
        sys.exit(1)

    hubs = sample_node_ids(data_dir, from_label, count, rng)
    if len(hubs) < count:
        print(f"WARN: only {len(hubs)} {from_label} nodes available", file=sys.stderr)
        count = len(hubs)

    targets_per_hub = fanout
    target_pool_size = count * targets_per_hub
    target_pool = sample_node_ids(data_dir, to_label, target_pool_size, rng)

    prop_columns = get_rel_property_columns(data_dir, rel_type)

    new_rows = []
    patterns = []
    pool_idx = 0
    for hub_idx in range(count):
        if pool_idx + targets_per_hub > len(target_pool):
            print(f"WARN: ran out of {to_label} targets after "
                  f"{hub_idx} hubs", file=sys.stderr)
            break
        targets = target_pool[pool_idx:pool_idx + targets_per_hub]
        pool_idx += targets_per_hub
        hub = hubs[hub_idx]

        hub_edges = []
        for target in targets:
            row = [hub, target] + ["" for _ in prop_columns]
            new_rows.append(row)
            hub_edges.append([hub, target])

        patterns.append({
            "pattern": "hub",
            "hub_id": f"hub_{hub_idx:06d}",
            "hub_node_id": hub,
            "hub_label": from_label,
            "fanout": targets_per_hub,
            "target_label": to_label,
            "rel_type": rel_type,
            "edges": hub_edges,
        })

    target_file = append_rel_rows(data_dir, rel_type, new_rows, prop_columns)
    return patterns, len(new_rows), target_file


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def parse_pattern_spec(spec):
    """
    Parse a single --pattern spec. Format varies by pattern type:

      cyclic:<count>:<min-max>:rel=<R>,node=<L>
        e.g. cyclic:50:3-5:rel=TRANSFERS_TO,node=Customer

      shared_attr:<count>:<min-max>:hub=<L>,member=<L>,rel=<R>
        e.g. shared_attr:100:5-10:hub=Device,member=Customer,rel=USES_DEVICE

      hub:<count>:fanout=<N>:rel=<R>
        e.g. hub:5:fanout=200:rel=TRANSFERS_TO

    Returns a dict with the parsed parameters, or raises ValueError.
    """
    # Split on colon — but the params section may contain commas with k=v pairs
    parts = spec.split(":", 3)
    if len(parts) < 3:
        raise ValueError(f"too few segments in '{spec}'")

    pattern_name = parts[0].strip()
    try:
        count = int(parts[1])
    except ValueError:
        raise ValueError(f"count must be integer in '{spec}'")

    out = {"pattern": pattern_name, "count": count}

    if pattern_name == "cyclic":
        if len(parts) < 4:
            raise ValueError(f"cyclic needs <min-max>:rel=<R>,node=<L> in '{spec}'")
        size_str, kv_str = parts[2], parts[3]
        cmin, cmax = (int(x) for x in size_str.split("-"))
        out["length_range"] = (cmin, cmax)
        kv = dict(kv.split("=") for kv in kv_str.split(","))
        out["rel_type"] = kv["rel"]
        out["node_label"] = kv["node"]

    elif pattern_name == "shared_attr":
        if len(parts) < 4:
            raise ValueError(f"shared_attr needs <min-max>:hub=...,member=...,rel=...")
        size_str, kv_str = parts[2], parts[3]
        cmin, cmax = (int(x) for x in size_str.split("-"))
        out["cluster_size_range"] = (cmin, cmax)
        kv = dict(kv.split("=") for kv in kv_str.split(","))
        out["hub_label"] = kv["hub"]
        out["member_label"] = kv["member"]
        out["rel_type"] = kv["rel"]

    elif pattern_name == "hub":
        # 'hub' has no min-max range, all params are k=v in parts[2]
        kv = dict(kv.split("=") for kv in parts[2].split(","))
        out["fanout"] = int(kv["fanout"])
        out["rel_type"] = kv["rel"]

    else:
        raise ValueError(f"unknown pattern '{pattern_name}'. "
                         f"Supported: cyclic, shared_attr, hub")

    return out


def main():
    parser = argparse.ArgumentParser(
        description="Inject analytical patterns into generate_data.py output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("data_dir", help="Directory containing CSVs and schema.json")
    parser.add_argument("--pattern", action="append", default=[],
                        help="Pattern spec; repeatable. See module docstring for syntax.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default 42).")
    args = parser.parse_args()

    if not args.pattern:
        print("ERROR: provide at least one --pattern spec", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    schema = load_schema(args.data_dir)

    all_patterns = []
    summary_per_spec = []

    for spec in args.pattern:
        try:
            params = parse_pattern_spec(spec)
        except (ValueError, KeyError) as e:
            print(f"ERROR: invalid --pattern '{spec}': {e}", file=sys.stderr)
            sys.exit(1)

        pname = params["pattern"]
        print(f"📌 Injecting {params['count']} '{pname}' pattern(s)…",
              file=sys.stderr)

        if pname == "cyclic":
            patterns, edges_added, target_file = inject_cyclic(
                schema, args.data_dir, params["count"], params["length_range"],
                params["rel_type"], params["node_label"], rng,
            )
        elif pname == "shared_attr":
            patterns, edges_added, target_file = inject_shared_attr(
                schema, args.data_dir, params["count"],
                params["cluster_size_range"], params["rel_type"],
                params["hub_label"], params["member_label"], rng,
            )
        elif pname == "hub":
            patterns, edges_added, target_file = inject_hub(
                schema, args.data_dir, params["count"],
                params["fanout"], params["rel_type"], rng,
            )
        else:
            print(f"ERROR: unknown pattern '{pname}'", file=sys.stderr)
            sys.exit(1)

        all_patterns.extend(patterns)
        summary_per_spec.append({
            "spec": spec,
            "patterns_planted": len(patterns),
            "edges_added": edges_added,
            "appended_to": os.path.basename(target_file),
        })
        print(f"   → {len(patterns)} planted, {edges_added} edges added "
              f"(into {os.path.basename(target_file)})", file=sys.stderr)

    # Write injected_patterns.json — the ground-truth manifest
    manifest_path = os.path.join(args.data_dir, "injected_patterns.json")
    with open(manifest_path, "w") as f:
        json.dump({
            "injected_at": datetime.now().isoformat(),
            "seed": args.seed,
            "specs": summary_per_spec,
            "patterns": all_patterns,
        }, f, indent=2)
    print(f"\n✅ Done. Manifest: {manifest_path}", file=sys.stderr)
    print(f"   Total patterns planted: {len(all_patterns)}", file=sys.stderr)


if __name__ == "__main__":
    main()
