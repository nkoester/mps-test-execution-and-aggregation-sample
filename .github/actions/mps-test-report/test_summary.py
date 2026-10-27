#!/usr/bin/env python3
"""Render MPS test results (JUnit XML) as a markdown summary with MPS node links.

Usage: test_summary.py <results-root> [--prefix P] [--mps-url URL] [--run-order NAMES] [--result-files PATTERNS]
                       [--show-passed] [--links FILE] [--combined-artifact NAME]

<results-root> contains one directory per downloaded artifact, named <prefix><category>-<name>, e.g.
test-results-interpreted-runInterpretedTests-no-build: the first segment after the prefix is the category (so a
category contains no '-'), the rest the run name (the category itself if there is none). Known categories
(CATEGORIES) come first with their display names, others follow under their raw name. --run-order lists run names
(newline or comma separated); within a category, listed runs come first in that order, the others follow by name.
--result-files are file name patterns (newline or comma separated), searched in any subdirectory; the defaults
cover interpreter tests and JUnit/Surefire/model checker reports. Passed tests are only counted unless
--show-passed is given. --links is an optional JSON file mapping artifact names to download URLs: each run
heading links its artifact, the top of the summary the --combined-artifact with all results.

Node links are taken from, in this order:
  1. the property 'nodeRef.<testcase name>', then 'nodeRef' (test case level before suite level)
  2. a node URL 'http://<host>:<port>/node?ref=<ref>' (optionally in brackets) in the failure message,
     then in the failure text
Interpreter tests provide 1, the model checker 2 (message). Generated tests have no node reference yet;
once their matchers append the node URL to the description (2), they get links without changes here.
Links open the node in a running MPS via its HTTP support plugin.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

# also the report order; unknown categories follow by name
CATEGORIES = {"modelcheck": "Model checker", "interpreted": "Interpreted tests", "generated": "Generated Java tests"}
STATUSES = ("passed", "failed", "error", "skipped")
ICONS = {"passed": "✅", "failed": "❌", "error": "💥", "skipped": "⏭️"}
DOWNLOAD = "⬇️"
# TESTS-TestSuites.xml (ant junitreport aggregate) intentionally does not match
DEFAULT_RESULT_FILES = ("InterpreterTestSuite*.xml", "TEST-*.xml")
JUNIT_ENGINE_SUITES = {"JUnit Jupiter", "JUnit Vintage", "JUnit Platform Suite"}
NODE_URL = re.compile(r"https?://[^\s\]]+/node\?ref=[^\s\]]+")
# a node URL, optionally in brackets, as appended to failure messages
NODE_URL_SUFFIX = re.compile(r"\s*\[?https?://[^\s\]]+/node\?ref=[^\s\]]+\]?")
# model checker messages start with the severity, e.g. 'Error: Type mismatch ...'
SEVERITY = re.compile(r"^(Error|Warning|Info):\s*")
# generated test names end with the node id of the test item, but carry no node reference to strip it with
NODE_ID_SUFFIX = re.compile(r"_\d{10,}$")
# with --show-passed: runs with fewer test cases are shown in a single table, larger ones fold their passed tests
FOLD_MIN_CASES = 5


def ref_from_text(*texts: str) -> str | None:
    for text in texts:
        if match := NODE_URL.search(text):
            return parse_qs(urlparse(match.group(0)).query).get("ref", [None])[0]
    return None


def properties(element: ET.Element) -> dict[str, str]:
    # only the element's own <properties>, not those of nested test cases
    block = element.find("properties")
    return {p.get("name"): p.get("value") for p in block.iter("property")} if block is not None else {}


def md(text: str, limit: int = 300) -> str:
    # node URLs in messages are already linked from the test name
    text = NODE_URL_SUFFIX.sub("", " ".join(text.split())).strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|")


def test_cell(base: str, case: dict) -> str:
    """Short test name, linked to its node if known, followed by the severity (model checker) or test class."""
    ref = case["ref"]
    node_id = ref.rsplit("/", 1)[-1] if ref else None
    if node_id and case["classname"].endswith("." + node_id):
        # model checker: classname is <root node presentation>.<node id>, the name repeats the message
        name = case["classname"].removesuffix("." + node_id)
        severity = SEVERITY.match(case["message"])
        detail = severity.group(1) if severity else ""
    else:
        # interpreter/generated: test case names end with the node id, e.g. brokenOnPurpose_item0_1515176184444827057;
        # JUnit 5 reports append the parameter list, e.g. brokenOnPurpose_item0_1515176184444827057()
        name = re.sub(r"\(.*\)$", "", case["name"])
        name = name.removesuffix("_" + node_id) if node_id else NODE_ID_SUFFIX.sub("", name)
        detail = case["suite"].rsplit(".", 1)[-1]
    name = md(name, 60)
    if ref:
        name = f"[{name.replace('[', '(').replace(']', ')')}]({base}/node?ref={quote(ref, safe='')})"
    return f"{name} · {md(detail, 60)}" if detail else name


def parse_file(path: Path):
    # interpreter results have a <testsuite> root, model checker results a <testsuites> root
    for suite in ET.parse(path).getroot().iter("testsuite"):
        suite_props = properties(suite)
        for case in suite.iter("testcase"):
            name = case.get("name", "")
            props = {**suite_props, **properties(case)}
            status, message, detail = "passed", "", ""
            for tag in ("failure", "error", "skipped"):
                el = case.find(tag)
                if el is not None:
                    status = "failed" if tag == "failure" else tag
                    detail = el.text or ""
                    # without a message attribute, the first line of the text (usually the exception) stands in
                    message = el.get("message") or detail.strip().split("\n", 1)[0]
                    break
            # node reference: interpreter properties (suite or test case level), else a node URL in the failure
            # message or text (model checker; generated tests once their matchers append it)
            plain = re.sub(r"\(.*\)$", "", name)
            suite_name = suite.get("name", path.stem)
            # JUnit 5 reports name the suite after the engine ('JUnit Jupiter'), the test class is the classname
            if suite_name in JUNIT_ENGINE_SUITES and case.get("classname"):
                suite_name = case.get("classname")
            # the model checker splits the model name into package (module part) and name (last segment)
            elif "." not in suite_name and suite.get("package"):
                suite_name = f"{suite.get('package')}.{suite_name}"
            yield {
                "suite": suite_name,
                "name": name,
                "classname": case.get("classname", ""),
                "time": float(case.get("time") or 0),
                "status": status,
                "message": message,
                "ref": props.get(f"nodeRef.{plain}") or props.get("nodeRef") or ref_from_text(message, detail),
            }


def split_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,\n]", value or "") if item.strip()]


def load_run(directory: Path, prefix: str, patterns: list[str]) -> dict:
    category, _, name = directory.name.removeprefix(prefix).partition("-")
    files = sorted({f for pattern in patterns for f in directory.rglob(pattern) if f.is_file()})
    return {
        "artifact": directory.name,
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


def case_table(cases: list[dict], base: str) -> list[str]:
    # failures first, then by suite/name
    order = {"error": 0, "failed": 1, "skipped": 2, "passed": 3}
    out = ["| | Test | Time (s) | Message |", "|---|---|---|---|"]
    for c in sorted(cases, key=lambda c: (order[c["status"]], c["suite"], c["name"])):
        message = SEVERITY.sub("", md(c["message"]))
        out.append(f"| {ICONS[c['status']]} | {test_cell(base, c)} | {c['time']:.3f} | {message} |")
    return out + [""]


def download_link(url: str | None, title: str) -> str:
    return f' [{DOWNLOAD}]({url} "Download {title}")' if url else ""


def run_section(run: dict, base: str, number: str, links: dict[str, str], show_passed: bool) -> list[str]:
    cases = run["cases"]
    s = stats(cases)
    out = [
        f"### {number} {icon(s)} {run['name']}{download_link(links.get(run['artifact']), run['artifact'])}",
        "",
        f"{s['tests']} tests: {s['passed']} passed, {s['failed']} failed, {s['error']} errors, "
        f"{s['skipped']} skipped, {s['time']:.3f} s",
        "",
    ]
    if not cases:
        # the model checker only reports failed checks
        return out + ["No findings." if run["files"] else "No result files found.", ""]
    # full suite names here, the table shows only the class name
    suites = sorted({c["suite"] for c in cases})
    out += [("Suite: " if len(suites) == 1 else "Suites: ") + ", ".join(f"`{s}`" for s in suites), ""]
    failures = [c for c in cases if c["status"] != "passed"]
    passed = [c for c in cases if c["status"] == "passed"]
    if not show_passed:
        return out + (case_table(failures, base) if failures else [])
    if len(cases) < FOLD_MIN_CASES:
        return out + case_table(cases, base)
    if failures:
        out += case_table(failures, base)
    if passed:
        # GitHub needs the blank line after <summary> to render the markdown table inside
        out += ["<details>", f"<summary>{len(passed)} passed</summary>", "", *case_table(passed, base), "</details>", ""]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Render MPS test results as a markdown summary.")
    parser.add_argument("root", type=Path, help="directory with one subdirectory per result artifact")
    parser.add_argument("--prefix", default="test-results-", help="artifact name prefix before <category>-<name>")
    parser.add_argument("--mps-url", default="http://127.0.0.1:63320", help="base URL of the MPS HTTP support")
    parser.add_argument("--run-order", default="", help="run names in display order (newline/comma separated)")
    parser.add_argument("--result-files", default="\n".join(DEFAULT_RESULT_FILES), help="result file name patterns")
    parser.add_argument("--show-passed", action="store_true", help="list passed tests, not only count them")
    parser.add_argument("--links", type=Path, help="JSON file mapping artifact names to download URLs")
    parser.add_argument("--combined-artifact", default="", help="artifact with all results, linked at the top")
    args = parser.parse_args()
    if not args.prefix:
        parser.error("--prefix must not be empty")
    patterns = split_list(args.result_files)
    if not patterns:
        parser.error("--result-files must name at least one pattern")

    root, prefix, base = args.root, args.prefix, args.mps_url.rstrip("/")
    run_rank = {n: i for i, n in enumerate(split_list(args.run_order))}
    links = json.loads(args.links.read_text()) if args.links and args.links.is_file() else {}
    combined = args.combined_artifact

    runs = [load_run(d, prefix, patterns) for d in sorted(root.iterdir()) if d.is_dir()] if root.is_dir() else []
    if not runs:
        print("# Test results\n\nNo test results found.")
        return 0

    # known categories in their defined order, then unknown ones by name; runs by run_order, then by name
    rank = {c: i for i, c in enumerate(CATEGORIES)}
    groups: dict[str, list[dict]] = {}
    for run in sorted(
        runs,
        key=lambda r: (
            rank.get(r["category"], len(rank)),
            r["category"],
            run_rank.get(r["name"], len(run_rank)),
            r["name"],
        ),
    ):
        groups.setdefault(run["category"], []).append(run)

    out = ["# Test results", ""]
    if combined and combined in links:
        out += [f"{DOWNLOAD} [All results]({links[combined]} \"Download {combined}\") as one archive", ""]
    out += overview(groups)
    for i, (category, category_runs) in enumerate(groups.items(), 1):
        s = stats([c for r in category_runs for c in r["cases"]])
        out += [f"## {i}. {icon(s)} {CATEGORIES.get(category, category)}", ""]
        for j, run in enumerate(category_runs, 1):
            out += run_section(run, base, f"{i}.{j}", links, args.show_passed)

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
