#!/usr/bin/env python3
"""Render MPS test results (JUnit XML) as a markdown summary with MPS node links.

Usage: test_summary.py <results-root> [<artifact-prefix>] [<mps-http-base>]

<results-root> contains one directory per downloaded artifact, named <artifact-prefix><category>-<name>,
e.g. test-results-interpreted-no-build. Known categories are listed in CATEGORIES; others are shown
under their raw name. Each directory holds InterpreterTestSuite*.xml (interpreter tests) or
TEST-*.xml (JUnit/Surefire, model checker) files.

Node links are taken from the testsuite properties 'nodeRef.<testcase name>' (falling back to
'nodeRef') or from a node URL '[http://<host>:<port>/node?ref=<ref>]' in the failure message. They
open the node in a running MPS via its HTTP support plugin.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

CATEGORIES = {"interpreted": "Interpreted tests", "generated": "Generated Java tests", "modelcheck": "Model checker"}
STATUSES = ("passed", "failed", "error", "skipped")
ICONS = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}
# TESTS-TestSuites.xml (ant junitreport aggregate) intentionally does not match
RESULT_FILES = ("InterpreterTestSuite*.xml", "TEST-*.xml")
NODE_URL = re.compile(r"https?://\S+/node\?ref=[^\s\]]+")


def ref_from_message(message: str) -> str | None:
    match = NODE_URL.search(message)
    return parse_qs(urlparse(match.group(0)).query).get("ref", [None])[0] if match else None


def md(text: str, limit: int = 300) -> str:
    # failure messages end with the node URL; it is already in the Node column
    text = re.sub(r"\s*\[https?://\S+/node\?ref=\S+\]\s*$", "", " ".join(text.split()))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def node_url(base: str, case: dict) -> str:
    ref = case["ref"]
    if not ref:
        return ""
    node_id = ref.rsplit("/", 1)[-1]
    if case["classname"].endswith("." + node_id):
        # model checker: classname is <root node presentation>.<node id>
        name = case["classname"].removesuffix("." + node_id)
    else:
        # interpreter: test case names end with the node id, e.g. brokenOnPurpose_item0_1515176184444827057
        name = case["name"].removesuffix("_" + node_id)
    name = md(name, 60).replace("[", "(").replace("]", ")")
    return f"[open {name} in MPS]({base}/node?ref={quote(ref, safe='')})"


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


def load_run(directory: Path, prefix: str) -> dict:
    category, _, name = directory.name.removeprefix(prefix).partition("-")
    if category not in CATEGORIES:
        category, name = directory.name.removeprefix(prefix), ""
    files = sorted({f for pattern in RESULT_FILES for f in directory.rglob(pattern)})
    return {
        "category": category,
        "name": name or category,
        "files": files,
        "cases": [c for f in files for c in parse_file(f)],
    }


def stats(cases: list[dict]) -> dict:
    counts = {s: sum(c["status"] == s for c in cases) for s in STATUSES}
    return {"tests": len(cases), **counts, "time": sum(c["time"] for c in cases)}


def icon(s: dict) -> str:
    return ICONS["failed"] if s["failed"] or s["error"] else ICONS["passed"]


def overview(groups: dict[str, list[dict]]) -> list[str]:
    out = [
        "| | Category | Tests | Passed | Failed | Errors | Skipped | Time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    all_cases = []
    for category, runs in groups.items():
        cases = [c for r in runs for c in r["cases"]]
        all_cases += cases
        s = stats(cases)
        out.append(
            f"| {icon(s)} | {CATEGORIES.get(category, category)} | {s['tests']} | {s['passed']} | {s['failed']} "
            f"| {s['error']} | {s['skipped']} | {s['time']:.3f} |"
        )
    s = stats(all_cases)
    out.append(
        f"| {icon(s)} | **Total** | **{s['tests']}** | **{s['passed']}** | **{s['failed']}** "
        f"| **{s['error']}** | **{s['skipped']}** | **{s['time']:.3f}** |"
    )
    return out + [""]


def run_section(run: dict, base: str) -> list[str]:
    s = stats(run["cases"])
    out = [
        f"### {icon(s)} {run['name']}",
        "",
        f"{s['tests']} tests: {s['passed']} passed, {s['failed']} failed, {s['error']} errors, "
        f"{s['skipped']} skipped, {s['time']:.3f} s",
        "",
    ]
    if not run["cases"]:
        # the model checker only reports failed checks
        return out + ["No findings." if run["files"] else "No result files found.", ""]
    out += ["| | Test | Suite | Time (s) | Node | Message |", "|---|---|---|---|---|---|"]
    # failures first, then by suite/name
    order = {"error": 0, "failed": 1, "skipped": 2, "passed": 3}
    for c in sorted(run["cases"], key=lambda c: (order[c["status"]], c["suite"], c["name"])):
        out.append(
            f"| {ICONS[c['status']]} | `{c['name']}` | `{c['suite']}` | {c['time']:.3f} "
            f"| {node_url(base, c)} | {md(c['message'])} |"
        )
    return out + [""]


def main() -> int:
    root = Path(sys.argv[1])
    prefix = sys.argv[2] if len(sys.argv) > 2 else "test-results-"
    base = (sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:63320").rstrip("/")

    runs = [load_run(d, prefix) for d in sorted(root.iterdir()) if d.is_dir()] if root.is_dir() else []
    if not runs:
        print("# Test results\n\nNo test results found.")
        return 0

    # known categories in their defined order, then unknown ones by name
    rank = {c: i for i, c in enumerate(CATEGORIES)}
    groups: dict[str, list[dict]] = {}
    for run in sorted(runs, key=lambda r: (rank.get(r["category"], len(rank)), r["category"], r["name"])):
        groups.setdefault(run["category"], []).append(run)

    out = ["# Test results", "", *overview(groups)]
    for category, category_runs in groups.items():
        s = stats([c for r in category_runs for c in r["cases"]])
        out += [f"## {icon(s)} {CATEGORIES.get(category, category)}", ""]
        for run in category_runs:
            out += run_section(run, base)

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
