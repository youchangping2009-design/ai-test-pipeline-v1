#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.score_oracle_delta import read_json, validate_and_score
from scripts.testcase_markdown_utils import parse_testcase_ids_from_content


ORACLE_FILES = (
    "reviews/blind_asset_freeze.json",
    "reviews/oracle_delta_input.json",
    "reviews/oracle_delta_score.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_artifact_path(item_root: Path, relative_path: str) -> Path:
    root = item_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"冻结清单路径越界: {relative_path}") from exc
    return candidate


def _all_feedback_applied(item_root: Path) -> bool:
    path = item_root / "design" / "design_feedback.json"
    if not path.is_file():
        return False
    payload = read_json(path)
    items = payload.get("feedback_items", [])
    return bool(items) and all(
        isinstance(item, dict) and item.get("status") == "applied"
        for item in items
    )


def validate_freeze(item_root: Path) -> tuple[str, ...]:
    freeze = read_json(item_root / "reviews" / "blind_asset_freeze.json")
    if freeze.get("oracle_excluded_from_generation") is not True:
        raise ValueError("blind_asset_freeze.oracle_excluded_from_generation 必须为 true")
    artifacts = freeze.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("blind_asset_freeze.artifacts 必须是非空对象")

    mismatches: list[str] = []
    for relative_path, expected_hash in artifacts.items():
        relative = str(relative_path).strip()
        expected = str(expected_hash).strip()
        if not relative or not expected:
            raise ValueError("冻结清单包含空路径或空 hash")
        artifact = _safe_artifact_path(item_root, relative)
        if not artifact.is_file():
            mismatches.append(f"{relative}: missing")
            continue
        actual = _sha256(artifact)
        if actual != expected:
            mismatches.append(f"{relative}: {actual} != {expected}")

    if not mismatches:
        return ()

    summary_mismatch = any(
        item.startswith("inputs/requirement_summary.md:")
        for item in mismatches
    )
    if summary_mismatch or not _all_feedback_applied(item_root):
        raise ValueError("冻结资产漂移:\n" + "\n".join(mismatches))
    return tuple(mismatches)


def validate_score(item_root: Path) -> dict[str, Any]:
    input_payload = read_json(item_root / "reviews" / "oracle_delta_input.json")
    testcase_ids = parse_testcase_ids_from_content(
        (item_root / "testcases" / "testcases_main.md").read_text(encoding="utf-8"),
        strict=True,
    )
    expected = validate_and_score(input_payload, testcase_ids)
    actual = read_json(item_root / "reviews" / "oracle_delta_score.json")
    expected.pop("generated_at", None)
    actual.pop("generated_at", None)
    if actual != expected:
        raise ValueError("oracle_delta_score.json 与当前输入/testcase 重新计算结果不一致")

    manifest = read_json(item_root / "manifest.json")
    for field in ("project_code", "work_item_id"):
        if input_payload.get(field) != manifest.get(field):
            raise ValueError(
                f"oracle_delta_input.{field} 与 manifest 不一致: "
                f"{input_payload.get(field)} != {manifest.get(field)}"
            )
    return expected


def validate_oracle_review(item_root: Path) -> dict[str, Any]:
    present = {
        relative: (item_root / relative).is_file()
        for relative in ORACLE_FILES
    }
    if not any(present.values()):
        return {"status": "not_applicable"}
    missing = [relative for relative, exists in present.items() if not exists]
    if missing:
        raise ValueError("Oracle Review 产物不完整: " + ", ".join(missing))

    freeze_mismatches = validate_freeze(item_root)
    score = validate_score(item_root)
    return {
        "status": (
            "post_feedback_regeneration"
            if freeze_mismatches
            else "frozen_baseline_intact"
        ),
        "freeze_mismatch_count": len(freeze_mismatches),
        "oracle_assertion_count": score["oracle_assertion_count"],
        "requirement_oracle_coverage_rate": score[
            "requirement_oracle_coverage_rate"
        ],
        "testcase_relevance_rate": score["testcase_relevance_rate"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="只读校验 Review 阶段的冻结资产与 Oracle delta 结果"
    )
    parser.add_argument("--item-root", required=True)
    args = parser.parse_args()
    try:
        result = validate_oracle_review(Path(args.item_root).resolve())
    except Exception as exc:
        print(f"❌ Oracle Review 校验失败: {exc}")
        return 1

    print("✅ Oracle Review 校验通过")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
