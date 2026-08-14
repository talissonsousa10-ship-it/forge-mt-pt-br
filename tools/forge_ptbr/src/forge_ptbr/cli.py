from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from forge_ptbr.paths import find_repo_root
from forge_ptbr.reporting.json_report import write_json_report
from forge_ptbr.scanner.service import scan_adventure


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge-ptbr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Inventory Adventure localization strings")
    scan.add_argument("--repo", type=Path)
    scan.add_argument("--output", type=Path)
    scan.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "scan":
        try:
            repo_root = find_repo_root(args.repo if args.repo is not None else Path.cwd())
            output = args.output
            if output is None:
                output = repo_root / "tools" / "forge_ptbr" / "build" / "inventory.json"
            report = scan_adventure(repo_root)
            write_json_report(report, output)
            if args.strict and report.unknown_entries:
                return 2
            return 0
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            print(f"forge-ptbr scan failed: {exc}", file=sys.stderr)
            return 1

    return 1
