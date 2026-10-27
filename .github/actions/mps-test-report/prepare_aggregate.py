#!/usr/bin/env python3
"""Prepare JUnit XML result files for Ant's junitreport (XMLResultAggregator).

Usage: prepare_aggregate.py <input-dir> <output-dir>

Writes one file per <testsuite> of every *.xml in <input-dir> to <output-dir>:
- files with a <testsuites> root (model checker) are split, junitreport only accepts a <testsuite> root
- junitreport takes the package from the suite name (everything before the last '.') and ignores the package
  attribute, so every suite gets its full name: suites named after the JUnit 5 engine ('JUnit Jupiter') the name
  of their test class, model checker suites (package = module part, name = last model name segment) the model name
- engine suites without test cases (e.g. an empty 'JUnit Vintage') are dropped
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# same names as in test_summary.py
JUNIT_ENGINE_SUITES = {"JUnit Jupiter", "JUnit Vintage", "JUnit Platform Suite"}


def main() -> int:
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    for path in sorted(source.glob("*.xml")):
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        for i, suite in enumerate(suites):
            name = suite.get("name", "")
            if name in JUNIT_ENGINE_SUITES:
                classname = next((c.get("classname") for c in suite.iter("testcase") if c.get("classname")), None)
                if classname is None:
                    continue
                suite.set("name", classname)
            elif "." not in name and suite.get("package"):
                suite.set("name", f"{suite.get('package')}.{name}")
            ET.ElementTree(suite).write(target / f"{path.stem}__{i}.xml", encoding="UTF-8", xml_declaration=True)
            written += 1
    print(f"{written} test suites prepared for the aggregated report")
    return 0


if __name__ == "__main__":
    sys.exit(main())
