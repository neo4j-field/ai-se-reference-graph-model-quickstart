---
name: graph-schema-editor
description: >
  Interactive visual graph schema editor for Neo4j property graph models. Use this skill whenever
  the user wants to design, create, draw, or model a graph schema, graph data model, Neo4j schema,
  property graph model, or node-relationship diagram. Also trigger when users mention arrows.app,
  ask to visually design nodes and relationships, want to create a Cypher schema, or ask to
  "draw a graph" in the data modeling sense (not charting/plotting). Trigger for phrases like
  "design a graph schema", "create a data model for Neo4j", "model my entities as a graph",
  "draw a node-relationship diagram", "create an arrows.app-style diagram", "help me with my
  Neo4j schema", "property graph model", or any request involving visual creation of nodes,
  labels, relationships, and properties for graph databases. Do NOT trigger for graph charts
  (bar/line/pie), mathematical graphs, or network visualization of existing data.
---

# Graph Schema Editor

This skill generates an interactive React artifact that lets users visually design Neo4j property
graph schemas — nodes, relationships, labels, and properties — directly in the Claude UI.

## When to Use

- User wants to design a graph data model or schema
- User mentions Neo4j, property graphs, Cypher schema, or arrows.app
- User asks to create/draw/model nodes and relationships
- User needs to export a schema as Cypher or arrows.app-compatible JSON
- User wants to iterate on a graph data model visually

## How It Works

1. Read the JSX template from `assets/graph-editor-template.jsx`
2. Customize the `initialGraph` object based on the user's domain/requirements
3. Output the customized JSX as a React artifact to `/mnt/user-data/outputs/`

## Step-by-Step Instructions

### Step 1: Understand the User's Domain

Before generating the editor, briefly understand what the user is modeling. Ask if unclear, but
if the user provides enough context (e.g., "movie database", "e-commerce system", "social network"),
proceed directly.

### Step 2: Read the Template

```
Read the file: assets/graph-editor-template.jsx
```

This is a complete, self-contained React component with:
- SVG canvas with pan, zoom (scroll wheel + buttons), double-click to add nodes
- Drag from node edges to create relationships (must land on a target node)
- Inspector sidebar for editing labels, properties, colors, radius
- Relationship list per node with individual delete buttons
- Fanned-out self-loops that don't overlap
- Export to arrows.app JSON and Cypher
- Import from arrows.app JSON

### Step 3: Customize the Initial Graph

Modify the `initialGraph` constant at the top of the file to pre-populate the editor with
nodes and relationships relevant to the user's domain. This is the key customization step.

**Rules for initialGraph:**

Each node needs:
- `id`: Unique string like "n0", "n1", etc.
- `position`: `{ x: number, y: number }` — spread nodes out (aim for ~200-300px apart)
- `caption`: The node label shown on the circle (e.g., "Person", "Movie")
- `labels`: Array of labels, typically `[caption]`
- `properties`: Object of `{ propertyName: "type" }` pairs (e.g., `{ name: "string", age: "integer" }`)
- `style`: `{ color: COLORS[index % COLORS.length], radius: 50 }`

Each relationship needs:
- `id`: Unique string like "r0", "r1", etc.
- `type`: Relationship type in UPPER_SNAKE_CASE (e.g., "ACTED_IN", "PURCHASED")
- `fromId`: Source node id
- `toId`: Target node id
- `properties`: Object of property key-type pairs (can be `{}`)

**Example initialGraph for an e-commerce domain:**

```javascript
const initialGraph = {
  nodes: [
    { id: "n0", position: { x: 200, y: 200 }, caption: "Customer", labels: ["Customer"], properties: { customerId: "string", name: "string", email: "string" }, style: { color: COLORS[0], radius: 50 } },
    { id: "n1", position: { x: 500, y: 200 }, caption: "Order", labels: ["Order"], properties: { orderId: "string", date: "datetime", total: "float" }, style: { color: COLORS[1], radius: 50 } },
    { id: "n2", position: { x: 800, y: 200 }, caption: "Product", labels: ["Product"], properties: { productId: "string", name: "string", price: "float" }, style: { color: COLORS[2], radius: 50 } },
    { id: "n3", position: { x: 500, y: 450 }, caption: "Category", labels: ["Category"], properties: { name: "string" }, style: { color: COLORS[3], radius: 50 } },
  ],
  relationships: [
    { id: "r0", type: "PLACED", fromId: "n0", toId: "n1", properties: {} },
    { id: "r1", type: "CONTAINS", fromId: "n1", toId: "n2", properties: { quantity: "integer" } },
    { id: "r2", type: "BELONGS_TO", fromId: "n2", toId: "n3", properties: {} },
  ],
  style: {},
};
```

**Layout tips:**
- Place nodes in a logical flow (left-to-right or top-to-bottom)
- Use ~250-300px spacing between connected nodes
- Keep the graph centered around (400, 300) for default viewport
- Assign different COLORS indices for visual distinction
- 3-6 nodes is ideal for a starting schema; the user can add more interactively

### Step 4: Output the Artifact

Save the customized JSX file to `/mnt/user-data/outputs/graph-schema-editor.jsx` and present it.

### Step 5: Explain What the User Can Do

After presenting, briefly mention:
- Double-click or "Add Node" button to add nodes
- Drag from node edge to another node to create relationships
- Click any element to edit in the sidebar
- Scroll wheel to zoom, drag canvas to pan
- Use the relationship list in the sidebar to manage overlapping edges
- Export button for arrows.app JSON or Cypher

## Important Notes

- The artifact is a **single self-contained JSX file** — no external dependencies beyond React,
  which is available in the Claude artifact runtime.
- The exported JSON is **compatible with arrows.app** — users can import it there for further
  editing or use it with tools like Neo4j Runway.
- The exported Cypher produces **CREATE statements** that can be run directly in Neo4j Browser.
- Always customize the initial graph to the user's domain — never output the default
  Person/Movie example unless the user is actually modeling a movie database.
- If the user uploads an arrows.app JSON file, read it and inject it as the initialGraph.
