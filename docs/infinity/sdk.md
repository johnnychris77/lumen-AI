# Project Infinity — Plugin SDK

LumenAI OS v5.0, Section 3.

## No modification of platform core required

`PlatformPlugin` (Genesis, v4.0) is a **metadata-only registration
surface** — the table's own docstring is explicit: "no plugin code is
ever imported or run by this table." Infinity's Plugin SDK extends it
additively with five new `registered_*_json` columns for the artifact
types the SDK names that it didn't yet have, rather than a second
plugin-registration table:

| SDK extension type | `PlatformPlugin` column |
|---|---|
| Applications | `registered_routes_json` (pre-existing) |
| Widgets | `registered_widgets_json` (pre-existing) |
| Dashboards | `registered_dashboards_json` (pre-existing) |
| Reports | `registered_reports_json` (pre-existing) |
| Workflow Nodes | `registered_workflow_nodes_json` (new) |
| AI Skills | `registered_ai_skills_json` (new) |
| Notifications | `registered_notifications_json` (new) |
| Commands | `registered_commands_json` (new) |
| Analytics | `registered_analytics_json` (new) |

Every registration is a JSON manifest entry — never executable code
imported into the platform process. A plugin can optionally link to a
`DeveloperAccount` and a `MarketplaceListing` (two new nullable columns),
so a marketplace-published skill/app and its plugin registration stay
connected.

```
POST /api/infinity/plugins
GET  /api/infinity/plugins
GET  /api/infinity/plugins/{plugin_key}
POST /api/infinity/plugins/{plugin_key}/extensions
POST /api/infinity/plugins/{plugin_key}/activate
POST /api/infinity/plugins/{plugin_key}/disable
```

See `docs/infinity/plugin-framework.md` for the Extension Framework
(Section 6) — a second, orthogonal dimension (*where* an extension
attaches in the UI) layered on top of these same registrations.
