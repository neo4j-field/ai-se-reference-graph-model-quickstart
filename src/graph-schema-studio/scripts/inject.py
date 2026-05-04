#!/usr/bin/env python3
"""
Unified injector for graph-schema-studio.

Reads a schema definition from one of several sources, normalises it into the
editor's initialGraph shape, and writes a ready-to-use React artifact to
/mnt/user-data/outputs/graph-schema-editor.jsx by default.

INPUT SOURCES
-------------
The script auto-detects the input source from the positional argument (or from
stdin when no argument is given):

  1. Reference-model ID (e.g. "claims-fraud"):
        python3 inject.py claims-fraud
     → resolves to references/claims-fraud.json in this skill

  2. File path (absolute or relative):
        python3 inject.py /home/claude/my_schema.json
     → reads that file

  3. Stdin (when no argument or when the argument is "-"):
        cat <<EOF | python3 inject.py
        { "nodes": [...], "relationships": [...] }
        EOF

  4. List available reference models:
        python3 inject.py --list

ACCEPTED SCHEMA SHAPES
----------------------
The normaliser accepts both the minimal custom shape and the full
reference-model shape, unwrapping common containers automatically:

  - Minimal custom:   { "nodes": [...], "relationships": [...] }
  - arrows.app:       { "graph": { "nodes": [...], "relationships": [...] } }
  - Reference model:  { "initialGraph": { "nodes": [...], "relationships": [...] }, ... }

In minimal custom schemas, relationship endpoints can be given as `from`/`to`
with node captions (the normaliser resolves them to ids) — or as explicit
`fromId`/`toId` when two nodes share a caption.

Any optional field (id, position, style, labels) is auto-filled with a
sensible default when omitted, but any value the caller DOES supply is
respected unchanged. This is what lets reference models keep their curated
positions and colours while custom domains stay terse.

OUTPUT
------
Pass an optional output path as the second positional argument:

    python3 inject.py claims-fraud /tmp/my-editor.jsx

Defaults to /mnt/user-data/outputs/graph-schema-editor.jsx.
"""
import json
import sys
import re
import os
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

TEMPLATE_PATH = os.path.join(SKILL_DIR, "assets", "graph-editor-template.jsx")
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

DEFAULT_OUTPUT = "/mnt/user-data/outputs/graph-schema-editor.jsx"

# Keep in sync with the COLORS array at the top of the JSX template
COLORS = [
    "#4C8BF5", "#E5484D", "#30A46C", "#E38627", "#8B5CF6",
    "#06B6D4", "#EC4899", "#F59E0B", "#6366F1", "#14B8A6",
]

DEFAULT_RADIUS = 55


# ---------------------------------------------------------------------------
# Reference model catalog
# ---------------------------------------------------------------------------
def list_reference_models():
    """Return the reference model catalog, preferring model-index.json."""
    index_path = os.path.join(REFERENCES_DIR, "model-index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return json.load(f).get("models", [])
    # Fallback: scan the references directory
    models = []
    if not os.path.isdir(REFERENCES_DIR):
        return models
    for f in sorted(os.listdir(REFERENCES_DIR)):
        if f.endswith(".json") and f != "model-index.json":
            with open(os.path.join(REFERENCES_DIR, f)) as fh:
                m = json.load(fh)
            models.append({
                "id": m.get("id", f[:-5]),
                "name": m.get("name", f[:-5]),
                "industry": m.get("industry", ""),
                "nodeCount": len(m.get("initialGraph", {}).get("nodes", [])),
                "relationshipCount": len(m.get("initialGraph", {}).get("relationships", [])),
            })
    return models


def print_reference_list():
    models = list_reference_models()
    if not models:
        print(f"No reference models found in {REFERENCES_DIR}", file=sys.stderr)
        sys.exit(1)
    print(f"{'ID':<42} {'Industry':<28} {'N':>3} {'R':>3}")
    print("-" * 80)
    for m in models:
        print(f"{m['id']:<42} {m.get('industry',''):<28} "
              f"{m.get('nodeCount','?'):>3} {m.get('relationshipCount','?'):>3}")
    print(f"\n{len(models)} reference models available in {REFERENCES_DIR}")


# ---------------------------------------------------------------------------
# Auto-layout for minimal schemas (nodes without explicit positions)
# ---------------------------------------------------------------------------
def auto_layout(n_nodes):
    """Return (x, y) positions arranged around a circle centred on the viewport."""
    if n_nodes == 0:
        return []
    if n_nodes == 1:
        return [(450, 350)]
    if n_nodes == 2:
        return [(300, 300), (600, 300)]
    cx, cy = 450, 350
    radius = max(180, 60 * n_nodes / (2 * math.pi))
    radius = min(radius, 320)
    positions = []
    for i in range(n_nodes):
        angle = -math.pi / 2 + (2 * math.pi * i / n_nodes)
        x = round(cx + radius * math.cos(angle))
        y = round(cy + radius * math.sin(angle))
        positions.append((x, y))
    return positions


# ---------------------------------------------------------------------------
# Schema normalisation: converts any accepted input shape to a full initialGraph
# ---------------------------------------------------------------------------
def unwrap(raw):
    """Unwrap common container keys so downstream logic sees a bare graph dict."""
    if isinstance(raw, dict):
        if "graph" in raw and isinstance(raw["graph"], dict):
            return raw["graph"]
        if "initialGraph" in raw and isinstance(raw["initialGraph"], dict):
            return raw["initialGraph"]
    return raw


def normalise_schema(raw):
    """Convert a minimal or fully-specified schema into a complete initialGraph."""
    raw = unwrap(raw)

    raw_nodes = raw.get("nodes") or []
    raw_rels = raw.get("relationships") or []

    if not isinstance(raw_nodes, list):
        raise ValueError("'nodes' must be a list")
    if not isinstance(raw_rels, list):
        raise ValueError("'relationships' must be a list")

    positions = auto_layout(len(raw_nodes))
    caption_to_id = {}
    duplicate_captions = set()
    nodes = []

    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict):
            raise ValueError(f"Node {i} is not an object")

        caption = n.get("caption") or (n.get("labels", [None])[0] if n.get("labels") else None)
        if not caption:
            raise ValueError(f"Node {i} is missing 'caption' (or 'labels')")

        nid = n.get("id") or f"n{i}"
        # Track duplicates but don't fail yet — duplicate captions are only a
        # problem if a relationship tries to resolve by caption later.
        if caption in caption_to_id and caption_to_id[caption] != nid:
            duplicate_captions.add(caption)
        else:
            caption_to_id[caption] = nid

        pos = n.get("position") or {"x": positions[i][0], "y": positions[i][1]}
        style = n.get("style") or {}
        color = style.get("color") or COLORS[i % len(COLORS)]
        radius = style.get("radius") or DEFAULT_RADIUS
        props = n.get("properties") or {}

        # Label normalisation: the labels array always starts with caption,
        # followed by any additional labels (Neo4j multi-label syntax
        # :Account:Internal). This invariant keeps the editor UI, the Cypher
        # export, and the arrows.app export consistent with each other.
        raw_labels = n.get("labels") or [caption]
        # Strip whitespace, drop empties, remove caption if it appears later
        # in the list (the invariant says it goes at index 0, once).
        seen = set()
        extras = []
        for lab in raw_labels:
            if not isinstance(lab, str):
                continue
            lab = lab.strip()
            if not lab or lab == caption or lab in seen:
                continue
            seen.add(lab)
            extras.append(lab)
        labels = [caption] + extras

        nodes.append({
            "id": nid,
            "position": {"x": pos["x"], "y": pos["y"]},
            "caption": caption,
            "labels": labels,
            "properties": props,
            "style": {"color": color, "radius": radius},
        })

    rels = []
    for i, r in enumerate(raw_rels):
        if not isinstance(r, dict):
            raise ValueError(f"Relationship {i} is not an object")

        rtype = r.get("type")
        if not rtype:
            raise ValueError(f"Relationship {i} is missing 'type'")

        # Explicit ids win. Only fall back to caption lookup when the caller
        # didn't supply them. Duplicate captions are only fatal if actually
        # consulted.
        from_id = r.get("fromId")
        if not from_id:
            from_caption = r.get("from")
            if from_caption in duplicate_captions:
                raise ValueError(
                    f"Relationship {i} ({rtype}): 'from' references duplicate "
                    f"caption '{from_caption}'. Use explicit fromId instead."
                )
            from_id = caption_to_id.get(from_caption)

        to_id = r.get("toId")
        if not to_id:
            to_caption = r.get("to")
            if to_caption in duplicate_captions:
                raise ValueError(
                    f"Relationship {i} ({rtype}): 'to' references duplicate "
                    f"caption '{to_caption}'. Use explicit toId instead."
                )
            to_id = caption_to_id.get(to_caption)

        if not from_id:
            raise ValueError(
                f"Relationship {i} ({rtype}): cannot resolve 'from' / 'fromId'. "
                f"Known captions: {list(caption_to_id.keys())}"
            )
        if not to_id:
            raise ValueError(
                f"Relationship {i} ({rtype}): cannot resolve 'to' / 'toId'. "
                f"Known captions: {list(caption_to_id.keys())}"
            )

        rid = r.get("id") or f"r{i}"
        rels.append({
            "id": rid,
            "type": rtype,
            "fromId": from_id,
            "toId": to_id,
            "properties": r.get("properties") or {},
        })

    return {"nodes": nodes, "relationships": rels}


# ---------------------------------------------------------------------------
# JS emission (same single-line-per-node format the editor expects)
# ---------------------------------------------------------------------------
def to_js_initial_graph(ig):
    lines = ["const initialGraph = {", "  nodes: ["]
    for n in ig["nodes"]:
        lines.append(
            f'    {{ id: "{n["id"]}", position: {json.dumps(n["position"])}, '
            f'caption: "{n["caption"]}", labels: {json.dumps(n["labels"])}, '
            f'properties: {json.dumps(n["properties"])}, style: {json.dumps(n["style"])} }},'
        )
    lines.append("  ],")
    lines.append("  relationships: [")
    for r in ig["relationships"]:
        lines.append(
            f'    {{ id: "{r["id"]}", type: "{r["type"]}", '
            f'fromId: "{r["fromId"]}", toId: "{r["toId"]}", '
            f'properties: {json.dumps(r["properties"])} }},'
        )
    lines.append("  ],")
    lines.append("  style: {},")
    lines.append("};")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input resolution
# ---------------------------------------------------------------------------
def resolve_input(arg):
    """Turn the user's argument into a raw parsed JSON dict + a source label.

    Tries in order:
      - arg is a readable file path
      - arg matches a reference model filename (references/<arg>.json or references/<arg>)
      - arg matches a reference model's `id` field (scans references/*.json)

    Returns (raw_dict, source_label, is_reference_model).
    """
    # 1. Explicit file path (absolute, relative, or just existing)
    if os.path.exists(arg):
        with open(arg) as f:
            return json.load(f), arg, False

    # 2. Reference model by filename
    if os.path.isdir(REFERENCES_DIR):
        candidate_id = os.path.join(REFERENCES_DIR, f"{arg}.json")
        if os.path.exists(candidate_id):
            with open(candidate_id) as f:
                return json.load(f), candidate_id, True
        candidate_file = os.path.join(REFERENCES_DIR, arg)
        if os.path.exists(candidate_file):
            with open(candidate_file) as f:
                return json.load(f), candidate_file, True

        # 3. Reference model by id field (handles cases where filename differs
        #    from the id — e.g. fraud-event-sequence lives in
        #    fraud-event-sequence-model.json)
        for fname in sorted(os.listdir(REFERENCES_DIR)):
            if not fname.endswith(".json") or fname == "model-index.json":
                continue
            fpath = os.path.join(REFERENCES_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict) and data.get("id") == arg:
                return data, fpath, True

    # 4. Not found
    hint = ""
    if os.path.isdir(REFERENCES_DIR):
        hint = " Run with --list to see reference model IDs."
    raise FileNotFoundError(f"Could not resolve '{arg}' as a file or reference model id.{hint}")


def read_stdin_json():
    if sys.stdin.isatty():
        print("ERROR: No input. Pipe schema JSON on stdin, pass a file path, or pass a reference model id.", file=sys.stderr)
        print_usage(sys.stderr)
        sys.exit(1)
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main injection routine
# ---------------------------------------------------------------------------
def inject(raw_schema, output_path, source_label=None, is_reference_model=False):
    ig = normalise_schema(raw_schema)

    if not os.path.exists(TEMPLATE_PATH):
        print(f"ERROR: Editor template not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(TEMPLATE_PATH, "r") as f:
        template = f.read()

    new_initial = to_js_initial_graph(ig)
    pattern = r"const initialGraph = \{[\s\S]*?\n\};"
    if not re.search(pattern, template):
        print("ERROR: Could not find 'const initialGraph = {...};' in template.", file=sys.stderr)
        sys.exit(1)

    output = re.sub(pattern, new_initial, template, count=1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(output)

    # Report
    if is_reference_model and source_label:
        # For reference models, surface name and source URL when available
        meta = raw_schema if isinstance(raw_schema, dict) else {}
        name = meta.get("name", os.path.basename(source_label))
        desc = meta.get("description", "")
        source = desc.split("Source: ")[-1] if "Source: " in desc else ""
        print(f"Model:  {name}")
        if source:
            print(f"Source: {source}")
    print(f"Nodes:  {len(ig['nodes'])}")
    print(f"Rels:   {len(ig['relationships'])}")
    print(f"Output: {output_path}")


def print_usage(stream=sys.stdout):
    print("Usage:", file=stream)
    print("  python3 inject.py <reference-model-id>       [output.jsx]", file=stream)
    print("  python3 inject.py <path/to/schema.json>      [output.jsx]", file=stream)
    print("  cat schema.json | python3 inject.py          [output.jsx]", file=stream)
    print("  python3 inject.py --list", file=stream)


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        print_usage()
        return

    if args and args[0] == "--list":
        print_reference_list()
        return

    # Optional trailing .jsx output path
    output_path = DEFAULT_OUTPUT
    if args and args[-1].endswith(".jsx"):
        output_path = args[-1]
        args = args[:-1]

    if len(args) > 1:
        print("ERROR: Too many arguments.", file=sys.stderr)
        print_usage(sys.stderr)
        sys.exit(1)

    source_label = None
    is_reference_model = False

    if len(args) == 1 and args[0] != "-":
        try:
            raw_schema, source_label, is_reference_model = resolve_input(args[0])
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in input file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_schema = read_stdin_json()

    try:
        inject(raw_schema, output_path, source_label=source_label,
               is_reference_model=is_reference_model)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
