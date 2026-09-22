from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "skills"
    / "reasoning-analysis"
    / "scripts"
    / "validate_reasoning_pack.py"
)
SPEC = importlib.util.spec_from_file_location("validate_reasoning_pack", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_semantic_grounding = MODULE.validate_semantic_grounding

from scripts.harness.stage_registry import resolve_stage_plan  # noqa: E402


def valid_pack(source_path: Path) -> dict:
    source_ref = {
        "source_type": "input_markdown",
        "path": str(source_path),
        "excerpt": "非目标协议 URL 必须被拒绝。",
    }
    return {
        "grounding_contract_version": "1.0",
        "explicit_rules": [
            {
                "id": "ER-001",
                "statement": "非目标协议 URL 必须被拒绝。",
                "source_refs": [source_ref],
            }
        ],
        "implicit_rules": [],
        "field_constraints": [],
        "data_source_rules": [],
        "business_risks": [],
        "edge_cases": [],
        "ambiguities": [],
        "recommended_test_dimensions": [
            {
                "dimension_id": "TD-001",
                "related_reasoning_ids": ["ER-001"],
            }
        ],
        "coverage_candidates": [
            {"candidate_id": "COV-001", "source_reasoning_ids": ["ER-001"]}
        ],
    }


class ReasoningGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.input_path = self.root / "work_item" / "analysis" / "reasoning_pack.json"
        self.input_path.parent.mkdir(parents=True)
        self.source_path = self.root / "work_item" / "inputs" / "requirement_summary.md"
        self.source_path.parent.mkdir(parents=True)
        self.source_path.write_text("非目标协议 URL 必须被拒绝。\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_valid_grounded_pack_passes(self) -> None:
        self.assertEqual(
            validate_semantic_grounding(valid_pack(self.source_path), self.input_path, True),
            [],
        )

    def test_ungrounded_content_is_rejected(self) -> None:
        pack = valid_pack(self.source_path)
        pack["business_risks"] = [
            {
                "risk_id": "RISK-001",
                "risk_statement": "无来源的旧样本业务风险。",
                "source_refs": [],
            }
        ]
        errors = validate_semantic_grounding(pack, self.input_path, True)
        self.assertTrue(any("缺少来源" in error for error in errors))

    def test_missing_or_mismatched_source_is_rejected(self) -> None:
        pack = valid_pack(self.source_path)
        pack["explicit_rules"][0]["source_refs"][0]["excerpt"] = "来源中不存在的内容"
        errors = validate_semantic_grounding(pack, self.input_path, True)
        self.assertTrue(any("无法在来源文件中回查" in error for error in errors))

    def test_dangling_and_empty_derived_references_are_rejected(self) -> None:
        pack = valid_pack(self.source_path)
        pack["recommended_test_dimensions"][0]["related_reasoning_ids"] = []
        pack["coverage_candidates"][0]["source_reasoning_ids"] = ["ER-MISSING"]
        errors = validate_semantic_grounding(pack, self.input_path, True)
        self.assertTrue(any("缺少 reasoning 引用" in error for error in errors))
        self.assertTrue(any("不存在的 reasoning ID" in error for error in errors))

    def test_contract_is_required_in_strict_mode(self) -> None:
        pack = valid_pack(self.source_path)
        pack.pop("grounding_contract_version")
        errors = validate_semantic_grounding(pack, self.input_path, True)
        self.assertTrue(any("要求声明 1.0" in error for error in errors))

    def test_harness_reasoning_stage_runs_grounding_validator(self) -> None:
        manifest = {
            "pipeline_policy": {"reasoning_grounding_required": True}
        }
        work_item_root = self.root / "harness-item"
        work_item_root.mkdir()
        (work_item_root / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        stage = next(
            item for item in resolve_stage_plan("M") if item.stage_id == "reasoning"
        )
        commands = stage.commands(work_item_root, "DEMO", "REQ-1", "M", True)

        self.assertEqual(stage.kind, "validation")
        self.assertEqual(len(commands), 1)
        self.assertIn("validate_reasoning_pack.py", commands[0][1])
        self.assertIn("--require-grounding-contract", commands[0])


if __name__ == "__main__":
    unittest.main()
