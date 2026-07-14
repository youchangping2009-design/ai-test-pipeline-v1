#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

ALLOWED_ROLLOUT_SOURCES = (
    "pt081_pilot",
    "new_work_item",
    "legacy_report_only",
)


def resolve_rollout_source(requested_rollout: str | None, work_item_id: str) -> str:
    normalized = (requested_rollout or "").strip()
    normalized_work_item_id = (work_item_id or "").strip().upper()

    # PT081 is the fixed pilot work item for the coverage-first quality gate.
    if normalized_work_item_id == "PT081":
        return "pt081_pilot"

    if normalized == "new_work_item":
        return "new_work_item"
    if normalized == "legacy_report_only":
        return "legacy_report_only"

    # Unsupported or stale rollout values fall back to legacy compare-only mode.
    return "legacy_report_only"
