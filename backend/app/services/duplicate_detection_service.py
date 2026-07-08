"""v2.2 — Duplicate Detection.

Detects real, verifiable problems across a session's captured images —
nothing here is guessed:

- **Duplicate images**: two tags in the same session share the exact same
  `image_sha256` — a byte-identical re-upload.
- **Wrong anatomy**: a tag's declared `anatomy_zone` is not actually a zone
  the resolved instrument family declares (app/services/instrument_anatomy.py)
  — the technician tagged a zone that doesn't exist for this instrument.
- **Wrong instrument**: two tags in the same session declare a different
  `instrument_family` — the session is internally inconsistent about what
  instrument is being inspected.

"Near duplicates" (visually similar but not byte-identical) would require
real image content/perceptual hashing, which this platform doesn't have —
honestly out of scope here rather than faked with a placeholder heuristic.
"""
from __future__ import annotations

from collections import defaultdict

from app.services.instrument_anatomy import get_anatomy, resolve_family


def detect_duplicates(tags: list[dict]) -> list[dict]:
    """Exact byte-identical duplicate images within one session, by
    `image_sha256`. Each finding lists every tag id sharing that hash."""
    by_hash: dict[str, list[dict]] = defaultdict(list)
    for t in tags:
        sha = t.get("image_sha256")
        if sha:
            by_hash[sha].append(t)

    findings = []
    for sha, group in by_hash.items():
        if len(group) > 1:
            findings.append({
                "type": "duplicate_image",
                "image_sha256": sha,
                "tag_ids": [t["id"] for t in group],
                "message": f"{len(group)} images share identical content (sha256 {sha[:12]}…) — likely a duplicate upload.",
            })
    return findings


def detect_wrong_anatomy(tags: list[dict]) -> list[dict]:
    """A tag's declared anatomy_zone that the resolved instrument family
    never declares — a mis-tagged zone, not a real anatomy finding."""
    findings = []
    for t in tags:
        zone = (t.get("anatomy_zone") or "").strip()
        if not zone:
            continue
        family_hint = t.get("instrument_family") or ""
        anatomy = get_anatomy(family_hint) if family_hint else None
        if anatomy is None:
            continue
        if zone not in anatomy["zone_names"]:
            findings.append({
                "type": "wrong_anatomy",
                "tag_id": t["id"],
                "declared_zone": zone,
                "instrument_family": anatomy["family"],
                "message": (
                    f"'{zone}' is not a declared anatomy zone for "
                    f"{anatomy['family'].replace('_', ' ')} — check the zone tag."
                ),
            })
    return findings


def detect_wrong_instrument(tags: list[dict]) -> list[dict]:
    """Internally inconsistent instrument_family across a single session's
    tags — the session appears to mix images from more than one instrument."""
    families = {
        resolve_family(t["instrument_family"]) if t.get("instrument_family") else None
        for t in tags
    }
    families.discard(None)
    if len(families) <= 1:
        return []
    return [{
        "type": "wrong_instrument",
        "families_seen": sorted(families),
        "message": (
            f"This session mixes images tagged for {len(families)} different "
            f"instrument families ({', '.join(sorted(families))}) — confirm every "
            "image belongs to the same instrument."
        ),
    }]


def detect_all(tags: list[dict]) -> dict:
    """All duplicate/anatomy/instrument findings for one session's tags.
    `tags` is a list of dicts with at least: id, image_sha256,
    anatomy_zone, instrument_family."""
    findings = [
        *detect_duplicates(tags),
        *detect_wrong_anatomy(tags),
        *detect_wrong_instrument(tags),
    ]
    return {
        "findings": findings,
        "has_warnings": bool(findings),
        "count": len(findings),
    }
