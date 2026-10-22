#!/usr/bin/env python3
"""Render interpreter and model check JUnit results as a markdown summary with MPS node links.

Usage: interpreter_test_summary.py <results-root> [<mps-http-base>]

<results-root> contains one directory per task (the downloaded artifacts), each holding
InterpreterTestSuite*.xml (interpreter tests) or TEST-*.xml (model checker) files. Node links are
taken from the testsuite properties 'nodeRef.<testcase name>' (falling back to 'nodeRef') or from
the node URL the model checker appends to its failure messages; they open the node in a running MPS
via its HTTP support plugin.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

ICONS = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}
RESULT_FILES = ("InterpreterTestSuite*.xml", "TEST-*.xml")
NODE_URL = re.compile(r"https?://\S+/node\?ref=[^\s\]]+")


def ref_from_message(message: str) -> str | None:
    match = NODE_URL.search(message)
    return parse_qs(urlparse(match.group(0)).query).get("ref", [None])[0] if match else None


def node_url(base: str, ref: str | None, test: str, classname: str) -> str:
    if not ref:
        return ""
    node_id = ref.rsplit("/", 1)[-1]
    if classname.endswith("." + node_id):
        # model checker: classname is <root node presentation>.<node id>
        name = classname.removesuffix("." + node_id)
    else:
        # interpreter: test case names end with the node id, e.g. brokenOnPurpose_item0_1515176184444827057
        name = test.removesuffix("_" + node_id)
    name = md(name, 60).replace("[", "(").replace("]", ")")
    return f"[open {name} in MPS]({base}/node?ref={quote(ref, safe='')})"


def md(text: str, limit: int = 300) -> str:
    # the executor appends the node URL to failure messages; it is already in the Node column
    text = re.sub(r"\s*\[https?://\S+/node\?ref=\S+\]\s*$", "", " ".join(text.split()))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def parse_file(path: Path):
    # interpreter results have a <testsuite> root, model checker results a <testsuites> root
    for suite in ET.parse(path).getroot().iter("testsuite"):
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
                "classname": case.get("classname", ""),
                "time": float(case.get("time") or 0),
                "status": status,
                "message": message,
                "ref": props.get(f"nodeRef.{name}") or props.get("nodeRef") or ref_from_message(message),
            }


def main() -> int:
    root = Path(sys.argv[1])
    base = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:63320").rstrip("/")
    out = ["# Test results", ""]

    task_dirs = sorted(d for d in root.iterdir() if d.is_dir()) if root.is_dir() else []
    if not task_dirs:
        out.append("No test results found.")

    for task_dir in task_dirs:
        files = sorted({f for pattern in RESULT_FILES for f in task_dir.rglob(pattern)})
        cases = [c for f in files for c in parse_file(f)]
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
            # the model checker only reports failed checks
            out += ["No findings." if files else "No result files found.", ""]
            continue
        out += ["| | Test | Suite | Time (s) | Node | Message |", "|---|---|---|---|---|---|"]
        # failures first, then by suite/name
        order = {"error": 0, "failed": 1, "skipped": 2, "passed": 3}
        for c in sorted(cases, key=lambda c: (order[c["status"]], c["suite"], c["name"])):
            out.append(
                f"| {ICONS[c['status']]} | `{c['name']}` | `{c['suite']}` | {c['time']:.3f} "
                f"| {node_url(base, c['ref'], c['name'], c['classname'])} | {md(c['message'])} |"
            )
        out.append("")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
