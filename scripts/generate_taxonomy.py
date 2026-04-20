#!/usr/bin/env python3

from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import pathlib
import re
import subprocess
import sys


DIAGNOSTIC_RE = re.compile(
    r"^(?:(?P<path>[^:(]+)\((?P<line>\d+)(?:,(?P<column>\d+))?\)\s+)?"
    r"(?P<level>Hint|Note|Warning|Error|Fatal):\s+(?P<message>.+)$"
)


@dataclasses.dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    category: str
    notes: str


@dataclasses.dataclass(frozen=True)
class Diagnostic:
    level: str
    message: str
    raw: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a markdown taxonomy for FPC diagnostics.")
    parser.add_argument("--log", required=True, type=pathlib.Path, help="Path to the captured FPC log.")
    parser.add_argument("--rules", required=True, type=pathlib.Path, help="TSV file with taxonomy rules.")
    parser.add_argument("--output", required=True, type=pathlib.Path, help="Where to write the markdown report.")
    return parser.parse_args()


def load_rules(path: pathlib.Path) -> list[Rule]:
    rules: list[Rule] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) != 3:
            raise SystemExit(f"{path}:{lineno}: expected 3 tab-separated fields, found {len(parts)}")
        pattern, category, notes = parts
        rules.append(Rule(re.compile(pattern, re.IGNORECASE), category, notes))
    return rules


def extract_diagnostics(path: pathlib.Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        match = DIAGNOSTIC_RE.match(raw)
        if not match:
            continue
        diagnostics.append(
            Diagnostic(
                level=match.group("level"),
                message=match.group("message").strip(),
                raw=raw.strip(),
            )
        )
    return diagnostics


def classify(message: str, rules: list[Rule]) -> tuple[str, str]:
    for rule in rules:
        if rule.pattern.search(message):
            return rule.category, rule.notes
    return "Unclassified", "Needs a new taxonomy rule or a broader category."


def detect_fpc_version() -> str:
    try:
        result = subprocess.run(
            ["fpc", "-iV"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def escape_cell(value: str) -> str:
    return value.replace("|", r"\|")


def render_report(
    diagnostics: list[Diagnostic],
    rules: list[Rule],
    log_path: pathlib.Path,
) -> str:
    category_order: list[str] = []
    seen_categories: set[str] = set()
    for rule in rules:
        if rule.category not in seen_categories:
            seen_categories.add(rule.category)
            category_order.append(rule.category)
    category_order.append("Unclassified")

    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    category_counts: collections.Counter[str] = collections.Counter()
    unclassified_raw: list[str] = []

    for diagnostic in diagnostics:
        category, notes = classify(diagnostic.message, rules)
        category_counts[category] += 1
        key = (category, diagnostic.level, diagnostic.message)
        bucket = grouped.setdefault(
            key,
            {"count": 0, "example": diagnostic.raw, "notes": notes},
        )
        bucket["count"] = int(bucket["count"]) + 1
        if category == "Unclassified":
            unclassified_raw.append(diagnostic.raw)

    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    fpc_version = detect_fpc_version()

    lines: list[str] = [
        "# FPC Error Taxonomy",
        "",
        f"- Generated: `{generated_at}`",
        f"- FPC version: `{fpc_version}`",
        f"- Log file: `{log_path.name}`",
        f"- Total diagnostics: `{len(diagnostics)}`",
        "",
        "## Counts by Category",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]

    for category in category_order:
        lines.append(f"| {escape_cell(category)} | {category_counts.get(category, 0)} |")

    lines.extend(["", "## Grouped Diagnostics", ""])

    for category in category_order:
        rows = [
            (level, message, details)
            for (group_category, level, message), details in grouped.items()
            if group_category == category
        ]
        if not rows:
            continue
        rows.sort(key=lambda row: (-int(row[2]["count"]), row[0], row[1]))
        lines.extend(
            [
                f"### {category}",
                "",
                "| Level | Count | Message | Notes | Example |",
                "| --- | ---: | --- | --- | --- |",
            ]
        )
        for level, message, details in rows:
            lines.append(
                "| {level} | {count} | {message} | {notes} | `{example}` |".format(
                    level=escape_cell(level),
                    count=details["count"],
                    message=escape_cell(message),
                    notes=escape_cell(str(details["notes"])),
                    example=escape_cell(str(details["example"])),
                )
            )
        lines.append("")

    if unclassified_raw:
        lines.extend(["## Unclassified Raw Lines", ""])
        for raw in sorted(set(unclassified_raw)):
            lines.append(f"- `{escape_cell(raw)}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    rules = load_rules(args.rules)
    diagnostics = extract_diagnostics(args.log)
    report = render_report(diagnostics, rules, args.log)
    args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
