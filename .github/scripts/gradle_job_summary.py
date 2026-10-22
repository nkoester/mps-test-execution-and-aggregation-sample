#!/usr/bin/env python3
"""Render the Gradle build overview of CI jobs as a markdown table (replaces the setup-gradle summary).

Usage: gradle_job_summary.py header
       gradle_job_summary.py row <requested-tasks> <step-outcome>

Each job records its row; the report job prints the header followed by all rows.

Versions are read from the version catalog, the Gradle version from the wrapper properties.
"""
import re
import sys
import tomllib
from pathlib import Path

OUTCOMES = {"success": "✅", "failure": "❌", "cancelled": "⏹️", "skipped": "⏭️"}
# label -> library alias in gradle/libs.versions.toml
DEPENDENCIES = {"extensions": "mps-extensions", "mbeddr": "mps-mbeddr", "iets3": "mps-iets3-opensource"}


def library_version(catalog: dict, alias: str) -> str:
    version = catalog["libraries"][alias]["version"]
    return catalog["versions"][version["ref"]] if isinstance(version, dict) else version


def main() -> int:
    if sys.argv[1] == "header":
        print("| Gradle Root Project | Requested Tasks | Gradle Version | Build Outcome | MPS Version | Dependencies |")
        print("|---|---|---|---|---|---|")
        return 0

    tasks, outcome = sys.argv[2], sys.argv[3]
    catalog = tomllib.loads(Path("gradle/libs.versions.toml").read_text())
    wrapper = Path("gradle/wrapper/gradle-wrapper.properties").read_text()
    settings = Path("settings.gradle.kts").read_text()

    gradle = re.search(r"gradle-([\w.\-]+?)-(?:bin|all)\.zip", wrapper)
    project = re.search(r'rootProject\.name\s*=\s*"([^"]+)"', settings)
    dependencies = "<br>".join(f"{label}: {library_version(catalog, alias)}" for label, alias in DEPENDENCIES.items())

    print(
        f"| {project.group(1) if project else '?'} | {tasks} | {gradle.group(1) if gradle else '?'} "
        f"| {OUTCOMES.get(outcome, outcome)} | {library_version(catalog, 'mps')} | {dependencies} |"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
