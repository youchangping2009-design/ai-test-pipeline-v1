#!/usr/bin/env python3
"""Inventory AI Test Pipeline work item inputs for requirement-summary work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".html",
    ".htm",
    ".xml",
}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
REQUIREMENT_SUMMARY_NAME = "requirement_summary.md"
SOURCE_MANIFEST_NAME = "source_manifest.json"


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for path in [cur, *cur.parents]:
        if (path / "START_HERE.md").exists() and (path / "WORKFLOW_CONTRACT.md").exists():
            return path
    raise SystemExit("Could not find ai-test-pipeline repo root from cwd")


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in TEXT_SUFFIXES:
        return "text"
    return "binary"


def preview_text(path: Path, limit: int = 500) -> str:
    if classify(path) != "text":
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return " ".join(text.split())[:limit]


def file_record(path: Path, root: Path) -> dict:
    stat = path.stat()
    return {
        "path": str(path.relative_to(root)),
        "kind": classify(path),
        "size_bytes": stat.st_size,
        "preview": preview_text(path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-code")
    parser.add_argument("--work-item-id")
    parser.add_argument("--work-item-dir")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    args = parser.parse_args()

    repo = find_repo_root(Path.cwd())

    if args.work_item_dir:
        work_item_dir = Path(args.work_item_dir)
        if not work_item_dir.is_absolute():
            work_item_dir = repo / work_item_dir
    else:
        if not args.project_code or not args.work_item_id:
            raise SystemExit("Provide --project-code and --work-item-id, or --work-item-dir")
        work_item_dir = repo / "assets" / "projects" / args.project_code / "work_items" / args.work_item_id

    inputs_dir = work_item_dir / "inputs"
    if not work_item_dir.exists():
        raise SystemExit(f"Work item dir not found: {work_item_dir}")
    if not inputs_dir.exists():
        raise SystemExit(f"Inputs dir not found: {inputs_dir}")

    files = sorted(p for p in inputs_dir.rglob("*") if p.is_file())
    records = [file_record(p, repo) for p in files]
    requirement_summary_path = inputs_dir / REQUIREMENT_SUMMARY_NAME
    source_manifest_path = inputs_dir / SOURCE_MANIFEST_NAME
    summary = {
        "repo_root": str(repo),
        "work_item_dir": str(work_item_dir.relative_to(repo)),
        "inputs_dir": str(inputs_dir.relative_to(repo)),
        "requirement_summary_path": str(requirement_summary_path.relative_to(repo)),
        "requirement_summary_exists": requirement_summary_path.exists(),
        "source_manifest_path": str(source_manifest_path.relative_to(repo)),
        "source_manifest_exists": source_manifest_path.exists(),
        "file_count": len(records),
        "by_kind": {
            "text": sum(1 for r in records if r["kind"] == "text"),
            "image": sum(1 for r in records if r["kind"] == "image"),
            "binary": sum(1 for r in records if r["kind"] == "binary"),
        },
        "files": records,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(f"repo_root: {summary['repo_root']}")
    print(f"work_item_dir: {summary['work_item_dir']}")
    print(f"inputs_dir: {summary['inputs_dir']}")
    print(f"requirement_summary_path: {summary['requirement_summary_path']}")
    print(f"requirement_summary_exists: {summary['requirement_summary_exists']}")
    print(f"source_manifest_path: {summary['source_manifest_path']}")
    print(f"source_manifest_exists: {summary['source_manifest_exists']}")
    print(f"file_count: {summary['file_count']} {summary['by_kind']}")
    for item in records:
        suffix = f" - {item['preview']}" if item["preview"] else ""
        print(f"- [{item['kind']}] {item['path']} ({item['size_bytes']} bytes){suffix}")


if __name__ == "__main__":
    main()
