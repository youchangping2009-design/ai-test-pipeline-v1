from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ReviewerSpec:
    reviewer: str
    skill_path: str
    readable_prefixes: Tuple[str, ...]
    readable_paths: Tuple[str, ...]


REVIEWER_SPECS = (
    ReviewerSpec(
        reviewer="evidence",
        skill_path="skills/evidence-reviewer/SKILL.md",
        readable_prefixes=(
            "evidence/",
            "image_evidence/",
            "structured_prd/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
        ),
        readable_paths=("manifest.json",),
    ),
    ReviewerSpec(
        reviewer="flow",
        skill_path="skills/flow-reviewer/SKILL.md",
        readable_prefixes=(
            "structured_prd/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
        ),
        readable_paths=("manifest.json",),
    ),
    ReviewerSpec(
        reviewer="testcase",
        skill_path="skills/testcase-reviewer/SKILL.md",
        readable_prefixes=(
            "structured_prd/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
        ),
        readable_paths=("manifest.json",),
    ),
)

REVIEWER_BY_NAME = {spec.reviewer: spec for spec in REVIEWER_SPECS}
REVIEWER_ORDER = tuple(spec.reviewer for spec in REVIEWER_SPECS)
