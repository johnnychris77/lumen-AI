# Marketing Website — Mobile Responsiveness Review

**Date:** 2026-08-02 • Method: source/layout inspection (Tailwind responsive utilities).
No device-lab/emulator captures were taken in this pass.

| Element | Approach | Status |
|---|---|---|
| Header/nav | Desktop `lg:flex`; below `lg`, hamburger + disclosure menu with focus ring. | PASS |
| Workflow diagram | `grid gap-4 sm:grid-cols-2` → **single column on phones**, two columns ≥ `sm`; keeps number, stage label, description. | PASS |
| Hero / headings | Fluid type (`text-…` with `sm:` steps), `max-w-` line-length caps. | PASS |
| CTAs | `flex flex-wrap gap-3`, `h-11` (≥44px touch target). | PASS |
| Footer | `grid md:grid-cols-[…]` collapses to one column. | PASS |
| Dashboard preview / charts | Synthetic charts inside responsive containers. | REVIEW — confirm no horizontal overflow < 360px. |
| Legend chips | `flex flex-wrap`. | PASS |

**Recommended verification:** open the deployed URL at 320/375/390/430/768/1024/1280/1440/1920
and confirm no horizontal scroll and no clipped workflow card. Layout uses only
responsive/relative units, so overflow risk is low.
