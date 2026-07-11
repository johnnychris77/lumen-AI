# Project Infinity — Extension Framework

LumenAI OS v5.0, Section 6.

## Two orthogonal dimensions, deliberately not conflated

* **Extension type** (`docs/infinity/sdk.md`, Section 3) — *what kind* of
  artifact a plugin registers (Application, Widget, Dashboard, Report,
  Workflow Node, AI Skill, Notification, Command, Analytics). Each maps
  1:1 onto one of `PlatformPlugin`'s `registered_*_json` columns.
* **Extension location** (Section 6) — *where in the UI* it attaches:
  Menu, Navigation, Dashboard, Command Center, Copilot, Reports, Digital
  Twin Panel, Knowledge Graph View, Simulation Model.

A location is recorded as a `location` key inside each registered JSON
item, not as a separate table or column — a single "dashboard" widget
can attach at several different locations (e.g. both the Command Center
and a Digital Twin Panel), so location is a property of the registration,
not a second classification axis on the plugin itself.

```
POST /api/infinity/plugins/{plugin_key}/extensions
{
  "extension_type": "dashboards",
  "location": "digital_twin_panel",
  "item": {"widget_key": "vendor-uptime-panel", "title": "Vendor Uptime"}
}
```

`infinity_extension_service.py` validates both `extension_type` (against
the 9 SDK types) and `location` (against the 9 named framework locations)
before appending — an unrecognized value on either axis is rejected with
a 422, never silently accepted into an unstructured registry.

No frontend widget-registry or dynamic component-loading mechanism
existed anywhere before Infinity (confirmed by grep — `PlatformAdmin
Dashboard.tsx` only renders a read-only list of `PlatformPlugin` rows).
This sprint establishes the backend registration surface; a future
sprint would need to build the actual frontend renderer that reads these
manifests and mounts real components at each location — that renderer is
explicitly out of scope here, matching the metadata-only convention
`PlatformPlugin` already established.
