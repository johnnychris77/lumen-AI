# Project Genesis — Modular Application Framework

LumenAI OS v4.0 — Section 3

## The module registry

`app/models/platform_core.py::PlatformModule` is the registry backing
the ten named modules the sprint asks for:

| Module | Category | Existing frontend routes it maps to |
|---|---|---|
| Inspect | clinical_operations | `/inspection/new`, `/inspection/capture`, `/findings`, `/inspection-work-queue`, `/operations-board`, `/operations`, `/clinical-readiness`, `/inspection-readiness`, `/inspection-zones` |
| Twin | clinical_operations | `/digital-twin` |
| Knowledge | intelligence | `/knowledge-graph`, `/knowledge-center`, `/anatomy-library`, `/instrument-library`, `/baseline-library` |
| Analytics | intelligence | `/analytics`, `/quality-intelligence`, `/quality-dashboard`, `/coverage-dashboard`, `/forecast` |
| Command | governance | `/quality-command-center`, `/sentinel`, `/executive-command-center`, `/pre-sterilization-command-center`, `/capa`, `/autonomous-operations` |
| Connect | coordination | `/case-intelligence`, `/integrations`, `/collaboration`, `/collaboration-governance`, `/atlas`, `/enterprise` |
| Academy | education | `/training-center`, `/training-compliance`, `/coaching-dashboard`, `/education-library` |
| Research | intelligence | `/research`, `/network-intelligence`, `/global-intelligence`, `/global-standards` |
| Developer | platform | `/agent-trace`, `/cios-dashboard` |
| Marketplace | platform | `/vendor-baseline-portal`, `/vendor-intelligence`, `/manufacturer-baselines` |

Every route listed above was grepped directly from
`frontend/src/main.tsx` before this table was written — nothing here is
invented. This is a **description layer**: `PlatformModule` records which
of this codebase's already-existing pages, permissions, and
documentation belong to which named module. No page was moved, no route
was renamed, and no existing component was rewritten to build this table.

## Each module has...

| Sprint's requirement | Where it lives |
|---|---|
| Routes | `PlatformModule.routes_json` — the existing frontend routes above |
| Permissions | `PlatformModule.permissions_json` — which roles may access it (drives `platform_navigation_service.visible_modules`'s permission filter) |
| Navigation | `nav_icon` + `category`, consumed by the Platform Launcher (Section 4) |
| Settings | `PlatformModule.settings_json` — free-form per-module settings, read/write via `update_module_settings` |
| Documentation | `documentation_url` — links to that module's existing `docs/<sprint>/` folder |
| Independent release lifecycle | `release_channel` (`stable`/`beta`) — flipping one module's channel via `set_release_channel` never touches any other module's row or code |

## Licensing gates visibility, not code

A module's code (its existing routes/pages) is always present in the
deployed app — `PlatformModuleLicense` (Section 1 Licensing) only gates
whether the Platform Launcher *surfaces* that module to a given tenant.
An unlicensed module's underlying routes remain reachable directly (they
already have their own RBAC from their original sprint) — Genesis adds a
licensing-aware navigation layer on top, it does not add a second
enforcement layer duplicating each module's existing access control.
