from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_and_score_testcases import (  # noqa: E402
    load_legacy_traceability_metric,
)


class ReviewScoreRetentionTests(unittest.TestCase):
    def test_missing_legacy_traceability_is_valid_for_minimal_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "traceability_matrix.json"

            rate, invalid_records = load_legacy_traceability_metric(
                missing,
                {},
                {"TC-001"},
            )

        self.assertEqual(rate, 0.0)
        self.assertEqual(invalid_records, [])


if __name__ == "__main__":
    unittest.main()
