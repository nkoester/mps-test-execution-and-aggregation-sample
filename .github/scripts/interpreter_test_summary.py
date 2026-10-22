#!/usr/bin/env python3
"""Render interpreter JUnit results as a markdown summary with MPS node links.

Usage: interpreter_test_summary.py <results-root> [<mps-http-base>]

<results-root> contains one directory per test task (the downloaded artifacts),
each holding InterpreterTestSuite*.xml files. The testsuite properties
'nodeRef.<testcase name>' (falling back to 'nodeRef') are turned into links
that open the node in a running MPS via its HTTP support plugin.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

ICONS = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}


def node_url(base: str, ref: str | None) -> str:
    return f"[open in MPS]({base}/node?ref={quote(ref, safe='')})" if ref else ""


def md(text: str, limit: int = 300) -> str:
    # the executor appends the node URL to failure messages; it is already in the Node column
    text = re.sub(r"\s*\[https?://\S+/node\?ref=\S+\]\s*$", "", " ".join(text.split()))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def parse_suite(path: Path):
    suite = ET.parse(path).getroot()
    props = {p.get("name"): p.get("value") for p in suite.iter("property")}
    for case in suite.iter("testcase"):
        name = case.get("name", "")
        status, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            el = case.find(tag)
            if el is not None:
                status = "failed" if tag == "failure" else tag
                message = el.get("message") or (el.text or "")
                break
        yield {
            "suite": suite.get("name", path.stem),
            "name": name,
            "time": float(case.get("time") or 0),
            "status": status,
            "message": message,
            "ref": props.get(f"nodeRef.{name}") or props.get("nodeRef"),
        }


def main() -> int:
    root = Path(sys.argv[1])
    base = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:63320").rstrip("/")
    out = ["# Interpreter test results", ""]

    task_dirs = sorted(d for d in root.iterdir() if d.is_dir()) if root.is_dir() else []
    if not task_dirs:
        out.append("No test results found.")

    for task_dir in task_dirs:
        cases = [c for f in sorted(task_dir.rglob("InterpreterTestSuite*.xml")) for c in parse_suite(f)]
        counts = {s: sum(c["status"] == s for c in cases) for s in ICONS}
        title = task_dir.name.removeprefix("test-results-")
        overall = ICONS["failed"] if counts["failed"] or counts["error"] else ICONS["passed"]
        out += [
            f"## {overall} {title}",
            "",
            f"{len(cases)} tests: {counts['passed']} passed, {counts['failed']} failed, "
            f"{counts['error']} errors, {counts['skipped']} skipped",
            "",
        ]
        if not cases:
            out += ["No InterpreterTestSuite*.xml found.", ""]
            continue
        out += ["| | Test | Suite | Time (s) | Node | Message |", "|---|---|---|---|---|---|"]
        # failures first, then by suite/name
        order = {"error": 0, "failed": 1, "skipped": 2, "passed": 3}
        for c in sorted(cases, key=lambda c: (order[c["status"]], c["suite"], c["name"])):
            out.append(
                f"| {ICONS[c['status']]} | `{c['name']}` | `{c['suite']}` | {c['time']:.3f} "
                f"| {node_url(base, c['ref'])} | {md(c['message'])} |"
            )
        out.append("")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
