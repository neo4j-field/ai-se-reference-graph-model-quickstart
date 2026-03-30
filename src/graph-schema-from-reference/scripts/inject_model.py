#!/usr/bin/env python3
"""
Injects a reference model's initialGraph into the graph-schema-editor template.

Usage:
    python inject_model.py <reference-model.json> <output.jsx>

The script auto-detects the graph-editor-template.jsx location from the
graph-schema-editor skill at /mnt/skills/user/graph-schema-editor/assets/.

Example:
    python inject_model.py \
      /mnt/skills/user/graph-reference-models/references/claims-fraud.json \
      /mnt/user-data/outputs/graph-schema-editor.jsx
"""
import json
import sys
import re
import os

# Auto-detect template location
TEMPLATE_PATHS = [
    "/mnt/skills/user/graph-schema-editor/assets/graph-editor-template.jsx",
    "/mnt/skills/private/graph-schema-editor/assets/graph-editor-template.jsx",
]

# Auto-detect reference model directory
# Looks in installed skill paths first, then relative to this script's parent skill
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
REFERENCE_DIRS = [
    "/mnt/skills/user/graph-reference-models/references",
    "/mnt/skills/private/graph-reference-models/references",
    os.path.join(SKILL_DIR, "references"),  # co-located references/ in same skill
]


def find_template():
    for p in TEMPLATE_PATHS:
        if os.path.exists(p):
            return p
    return None


def find_reference_dir():
    for d in REFERENCE_DIRS:
        if os.path.isdir(d):
            return d
    return None


def list_models(ref_dir):
    """List available models from the reference directory."""
    index_path = os.path.join(ref_dir, "model-index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
        return index.get("models", [])
    # Fallback: scan JSON files
    models = []
    for f in sorted(os.listdir(ref_dir)):
        if f.endswith(".json") and f != "model-index.json":
            with open(os.path.join(ref_dir, f)) as fh:
                m = json.load(fh)
            models.append({"id": m["id"], "name": m["name"], "file": f,
                           "industry": m.get("industry", ""),
                           "nodeCount": len(m["initialGraph"]["nodes"]),
                           "relationshipCount": len(m["initialGraph"]["relationships"])})
    return models


def json_to_js_initialGraph(model_json):
    """Convert the reference model JSON's initialGraph to a JS const declaration."""
    ig = model_json["initialGraph"]
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


def inject(model_path, template_path, output_path):
    """Read the model JSON, read the template JSX, replace initialGraph, write output."""
    with open(model_path, "r") as f:
        model = json.load(f)

    with open(template_path, "r") as f:
        template = f.read()

    new_initial = json_to_js_initialGraph(model)

    pattern = r"const initialGraph = \{[\s\S]*?\n\};"
    if not re.search(pattern, template):
        print("ERROR: Could not find 'const initialGraph = {...};' in template", file=sys.stderr)
        sys.exit(1)

    output = re.sub(pattern, new_initial, template, count=1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(output)

    node_count = len(model["initialGraph"]["nodes"])
    rel_count = len(model["initialGraph"]["relationships"])
    source = ""
    desc = model.get("description", "")
    if "Source: " in desc:
        source = desc.split("Source: ")[-1]

    print(f"Model:  {model['name']}")
    print(f"Nodes:  {node_count}")
    print(f"Rels:   {rel_count}")
    if source:
        print(f"Source: {source}")
    print(f"Output: {output_path}")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        ref_dir = find_reference_dir()
        if not ref_dir:
            print("ERROR: Cannot find reference models directory", file=sys.stderr)
            sys.exit(1)
        models = list_models(ref_dir)
        print(f"{'ID':<42} {'Industry':<28} {'N':>3} {'R':>3}")
        print("-" * 80)
        for m in models:
            print(f"{m['id']:<42} {m.get('industry',''):<28} {m.get('nodeCount','?'):>3} {m.get('relationshipCount','?'):>3}")
        return

    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python inject_model.py <model-id-or-path.json> [output.jsx]")
        print("       python inject_model.py --list")
        sys.exit(1)

    model_input = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) == 3 else "/mnt/user-data/outputs/graph-schema-editor.jsx"

    # Resolve model path: accept model ID, filename, or full path
    if os.path.exists(model_input):
        model_path = model_input
    else:
        ref_dir = find_reference_dir()
        if ref_dir:
            # Try as model ID
            candidate = os.path.join(ref_dir, f"{model_input}.json")
            if os.path.exists(candidate):
                model_path = candidate
            else:
                # Try as filename
                candidate = os.path.join(ref_dir, model_input)
                if os.path.exists(candidate):
                    model_path = candidate
                else:
                    print(f"ERROR: Cannot find model '{model_input}'", file=sys.stderr)
                    print(f"  Tried: {candidate}", file=sys.stderr)
                    print(f"  Run with --list to see available models", file=sys.stderr)
                    sys.exit(1)
        else:
            print(f"ERROR: Cannot find reference models directory or file '{model_input}'", file=sys.stderr)
            sys.exit(1)

    # Find template
    template_path = find_template()
    if not template_path:
        print("ERROR: Cannot find graph-editor-template.jsx", file=sys.stderr)
        print(f"  Searched: {TEMPLATE_PATHS}", file=sys.stderr)
        sys.exit(1)

    inject(model_path, template_path, output_path)


if __name__ == "__main__":
    main()
