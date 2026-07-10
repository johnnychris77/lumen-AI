# Project Forge — Workflow Builder

LumenAI OS v4.1 — Section 1

## No existing diagram library — a small custom canvas, not a new dependency

Before writing any frontend code, `frontend/package.json` and every
component under `frontend/src` were checked for an existing visual/
canvas/drag-and-drop diagram library (`reactflow`, `dagre`, `konva`,
`cytoscape`, `d3`, `vis-*`) — none exist; only `recharts` for charts.
Rather than add a new npm dependency for a single sprint's canvas,
`WorkflowBuilderDashboard.tsx` implements a small, self-contained SVG/
HTML node editor:

- **Nodes** are absolutely-positioned `<div>`s whose logical `(x, y)`
  coordinates live in React state; dragging updates that state directly
  (no external drag library).
- **Connections** are plain SVG `<line>` elements computed from each
  node's logical position — no separate edge-rendering library.
- **Zoom** scales each node's *rendered* position/size directly
  (`node.x * zoom`) rather than a CSS `transform: scale(...)` — this
  keeps the browser's native scrollbars usable for **panning** without
  the extra complexity of reconciling a CSS transform with scroll
  offsets.
- **Auto-layout** (`autoLayout()` in the component) is a real breadth-
  first layering computed from the workflow's own edges starting at its
  `start` node — nodes are assigned `x = depth * 220`, `y = index-within-
  layer * 140`. It is a genuine graph traversal over the workflow's real
  edge list, not a cosmetic shuffle.

## Node types

All sixteen node types the sprint names are enumerated once, in
`app/models/workflow_forge.py::NODE_TYPES`, and rendered as the palette
in the builder: Start, Inspection, AI Analysis, Anatomy Check, Coverage
Check, Knowledge Lookup, Digital Twin Update, Clinical Reasoning,
Supervisor Review, Conditional Branch, Notification, Approval, Repair
Referral, Knowledge Capture, Export Report, End.

## Data model

A workflow is one `WorkflowDefinition` row: `nodes_json` (each node:
`{key, type, label, x, y, config}`) and `edges_json` (each edge:
`{from, to, condition?}` — `condition` is `"true"`/`"false"` for a
Conditional Branch or Coverage Check node's two outgoing paths).
`forge_workflow_service.py` validates every node's `type` against
`NODE_TYPES` before persisting — an unknown node type is rejected at
creation time (`422`), never silently accepted.

## Endpoints

```
POST /api/forge/workflows                 — create (draft, version 1)
GET  /api/forge/workflows                 — list (tenant's own + global templates)
GET  /api/forge/workflows/{id}
POST /api/forge/workflows/{id}/revise      — edit a draft in place, or fork a published one into a new draft version
POST /api/forge/workflows/{id}/publish
POST /api/forge/workflows/{id}/archive
```

See `docs/forge/workflow-versioning.md` for the version/rollback model
and `docs/forge/clinical-rule-engine.md` for how a Conditional Branch
node's `config.rule_id` is evaluated during execution.
