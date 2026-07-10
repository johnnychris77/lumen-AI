# Project Genesis — Plugin Framework

LumenAI OS v4.0 — Section 8

## What this is — and, explicitly, what it is not

`PlatformPlugin` (`app/models/platform_core.py`) is a **registration and
catalog surface**: a future module announces the routes, menus,
permissions, widgets, dashboards, and reports it wants to contribute as
descriptive JSON. Registering, activating, or disabling a plugin via
`platform_plugin_service.py` is a pure data operation against this one
table.

It is **not** a dynamic code-loading, sandboxed plugin execution engine.
No plugin code is ever imported, compiled, or run as a result of any
function in this module. Being explicit about that boundary here is
deliberate — this sprint does not build (and this document does not
claim) a live third-party code execution sandbox, which would be a much
larger, security-sensitive undertaking (arbitrary code execution,
sandboxing, resource limits, supply-chain review) outside this sprint's
actual scope. "No core modifications required" is satisfied in the sense
that matters today: registering a plugin's intent never requires editing
`app/main.py` or any existing router.

## Lifecycle

```
draft --activate--> active --disable--> disabled
```

- `register_plugin(...)` — creates a new `PlatformPlugin` row in
  `draft` status. Raises `DuplicatePluginKeyError` if `plugin_key` is
  already registered.
- `activate_plugin(plugin_key)` / `disable_plugin(plugin_key)` — status
  transitions. Raises `UnknownPluginError` for an unregistered key.
- `list_plugins(status=...)` / `get_plugin(plugin_key)` — read paths.

## Endpoints

```
POST /api/platform/plugins
GET  /api/platform/plugins
POST /api/platform/plugins/{plugin_key}/activate
POST /api/platform/plugins/{plugin_key}/disable
```

## Event bus integration

Registering a plugin is exactly the kind of platform-level occurrence
Nexus's event bus (`app/services/nexus_event_bus_service.py`) was built
to carry — `NEXUS_EVENT_TYPES` was extended with `PluginRegistered`
(and `ModuleLicenseChanged` for Section 1's licensing) for this purpose,
reusing the existing bus rather than adding a second one.
