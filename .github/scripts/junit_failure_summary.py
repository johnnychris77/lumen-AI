#!/usr/bin/env python3
"""Print the failed and errored tests of a JUnit XML file as GitHub annotations
and append them to the job's step summary (P472-03 B7.2).

Writes test names and the first line of each failure message only; no captured
output. Exits 0 so it never masks or replaces the test step's own result.
"""
import os
import sys
import xml.etree.ElementTree as ET


def main(path: str) -> int:
    if not os.path.exists(path):
        print(f"::warning::no JUnit file at {path} (the suite may not have started)")
        return 0
    rows = []
    for case in ET.parse(path).getroot().iter("testcase"):
        for tag in ("failure", "error"):
            node = case.find(tag)
            if node is not None:
                first = ((node.get("message") or node.text or "").strip().splitlines() or [""])[0][:300]
                rows.append((tag, f"{case.get('classname')}::{case.get('name')}", first))
    for tag, name, msg in rows:
        print(f"::error title=pytest {tag}::{name} — {msg}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### {len(rows)} failed/errored test(s) in `{os.path.basename(path)}`\n\n")
            for tag, name, msg in rows:
                fh.write(f"- **{tag}** `{name}` — {msg.replace('|', '/')}\n")
    print(f"{len(rows)} failed/errored test(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "test-results/pytest.xml"))
