from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from forge_ptbr.catalog.store import catalog_path, load_all_catalogs, write_catalog
from forge_ptbr.catalog.sync import sync_catalogs
from forge_ptbr.glossary.store import load_glossary
from forge_ptbr.memory.store import load_memory, promote_approved, write_memory
from forge_ptbr.paths import find_repo_root
from forge_ptbr.reporting.json_report import write_json_report
from forge_ptbr.scanner.service import scan_adventure
from forge_ptbr.translator.factory import make_provider
from forge_ptbr.translator.service import translate_catalog_entry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge-ptbr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Inventory Adventure localization strings")
    scan.add_argument("--repo", type=Path)
    scan.add_argument("--output", type=Path)
    scan.add_argument("--strict", action="store_true")

    catalog_sync = subparsers.add_parser("catalog-sync", help="Synchronize translation catalogs")
    catalog_sync.add_argument("--repo", type=Path)
    catalog_sync.add_argument("--catalogs-dir", type=Path)

    translate = subparsers.add_parser("translate", help="Automatically translate eligible catalog entries")
    translate.add_argument("--repo", type=Path)
    translate.add_argument("--catalogs-dir", type=Path)
    translate.add_argument("--memory", type=Path)
    translate.add_argument("--glossary", type=Path)
    translate.add_argument("--provider", default="argos")
    return parser


def _repo_root(value: Path | None) -> Path:
    return find_repo_root(value if value is not None else Path.cwd())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "scan":
        try:
            repo_root = _repo_root(args.repo)
            output = args.output or repo_root / "tools" / "forge_ptbr" / "build" / "inventory.json"
            report = scan_adventure(repo_root)
            write_json_report(report, output)
            if args.strict and report.unknown_entries:
                return 2
            return 0
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
            print(f"forge-ptbr scan failed: {exc}", file=sys.stderr)
            return 1

    if args.command == "catalog-sync":
        try:
            repo_root = _repo_root(args.repo)
            catalogs_dir = args.catalogs_dir or repo_root / "translations" / "catalogs"
            summary = sync_catalogs(scan_adventure(repo_root), catalogs_dir)
            print(
                "catalog-sync: "
                f"total={summary.total} new={summary.new} changed={summary.changed} "
                f"obsolete={summary.obsolete} approved={summary.approved}"
            )
            return 0
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
            print(f"forge-ptbr catalog-sync failed: {exc}", file=sys.stderr)
            return 1

    if args.command == "translate":
        try:
            repo_root = _repo_root(args.repo)
            catalogs_dir = args.catalogs_dir or repo_root / "translations" / "catalogs"
            memory_path = args.memory or repo_root / "translations" / "memory.json"
            glossary_path = args.glossary or repo_root / "translations" / "glossary" / "mtg-pt-BR.json"

            provider = make_provider(args.provider)
            if not provider.is_ready():
                print(f"forge-ptbr translate: provider '{args.provider}' is not ready", file=sys.stderr)
                return 3

            catalogs = load_all_catalogs(catalogs_dir)
            all_entries = [entry for entries in catalogs.values() for entry in entries]
            memory_records = promote_approved(all_entries, load_memory(memory_path))
            glossary_terms = load_glossary(glossary_path)

            translated = 0
            for entries in catalogs.values():
                for entry in entries:
                    if translate_catalog_entry(entry, provider, memory_records, glossary_terms):
                        translated += 1

            for plane, entries in catalogs.items():
                write_catalog(catalog_path(catalogs_dir, plane), plane, entries)
            write_memory(memory_path, memory_records)
            print(f"translate: processed={translated} provider={provider.name}")
            return 0
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError, RuntimeError) as exc:
            print(f"forge-ptbr translate failed: {exc}", file=sys.stderr)
            return 1

    return 1
