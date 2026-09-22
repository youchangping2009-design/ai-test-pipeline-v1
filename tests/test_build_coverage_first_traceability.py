from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_coverage_first_traceability import infer_rule_id  # noqa: E402


class CoverageFirstTraceabilityTests(unittest.TestCase):
    def test_uses_structured_explicit_rule_id_without_er_prefix_assumption(self) -> None:
        entry = {
            "rule_name": "GRA-R001",
            "structured_refs": ["requirement_info.explicit_rules.GRA-R001"],
            "module_name": "APIStore 序列化",
            "feature_name": "资源序列化选择",
            "coverage_type": "happy_path_combo",
        }

        self.assertEqual(infer_rule_id(entry), "GRA-R001")

    def test_keeps_context_fallback_for_non_identifier_rule_name(self) -> None:
        entry = {
            "rule_name": "字段展示规则",
            "structured_refs": [],
            "module_name": "配置管理",
            "feature_name": "字段设置",
            "field_name": "display_name",
            "coverage_type": "display_rule",
        }

        self.assertEqual(
            infer_rule_id(entry),
            "配置管理::字段设置::display_name::display_rule",
        )


if __name__ == "__main__":
    unittest.main()
