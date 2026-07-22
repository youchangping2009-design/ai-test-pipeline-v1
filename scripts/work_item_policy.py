#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_WORK_ITEM_LEVELS = {"S", "M", "L"}
DEFAULT_WORK_ITEM_LEVEL = "M"


def normalize_work_item_level(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if not normalized:
        return None
    if normalized not in VALID_WORK_ITEM_LEVELS:
        raise ValueError(f"work_item_level 必须是 S/M/L，实际: {value}")
    return normalized


def resolve_work_item_level(
    manifest: dict[str, Any] | None,
    cli_level: str | None = None,
) -> tuple[str, str]:
    cli_value = normalize_work_item_level(cli_level)
    if cli_value:
        return cli_value, "cli"

    manifest_value = normalize_work_item_level(
        manifest.get("work_item_level") if isinstance(manifest, dict) else None
    )
    if manifest_value:
        return manifest_value, "manifest"
    return DEFAULT_WORK_ITEM_LEVEL, "default"


def persist_default_work_item_level(manifest_path: Path) -> tuple[str, bool]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest.json 必须为 JSON object")
    level, source = resolve_work_item_level(payload)
    if source == "manifest":
        return level, False
    payload["work_item_level"] = level
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return level, True
