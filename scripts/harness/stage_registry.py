from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
CommandFactory = Callable[[Path, str, str, str, bool], list[list[str]]]


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    kind: str
    levels: frozenset[str]
    required_files: tuple[str, ...]
    command_factory: CommandFactory

    def commands(
        self,
        item_root: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        strict: bool,
    ) -> list[list[str]]:
        return self.command_factory(
            item_root,
            project_code,
            work_item_id,
            work_item_level,
            strict,
        )


def _python(script: str, *args: str) -> list[str]:
    return [sys.executable, str(ROOT / script), *args]


def _no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


def _requirement_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    strict: bool,
) -> list[list[str]]:
    command = _python(
        "skills/requirement-summary/scripts/validate_requirement_sources.py",
        "--input",
        str(item_root / "inputs" / "source_manifest.json"),
    )
    if strict:
        command.append("--strict")
    return [command]


def _structured_prd_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/prd-structuring/scripts/validate_structured_prd.py",
            "--input",
            str(item_root / "structured_prd" / "structured_prd.json"),
            "--schema",
            str(ROOT / "schemas" / "structured_prd.schema.json"),
        )
    ]


def _coverage_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/coverage-planning/scripts/validate_coverage_matrix.py",
            "--input",
            str(item_root / "coverage" / "coverage_matrix.json"),
            "--schema",
            str(ROOT / "schemas" / "coverage_matrix.schema.json"),
        )
    ]


def _testability_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/testability-gate/scripts/validate_testability_gate.py",
            "--input",
            str(item_root / "acceptance" / "testability_gate.json"),
            "--structured-prd",
            str(item_root / "structured_prd" / "structured_prd.json"),
        )
    ]


def _acceptance_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/acceptance-example/scripts/validate_acceptance_examples.py",
            "--input",
            str(item_root / "acceptance" / "acceptance_examples.json"),
            "--testability-gate",
            str(item_root / "acceptance" / "testability_gate.json"),
        )
    ]


def _responsibility_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/test-design/scripts/validate_responsibility_map.py",
            "--input",
            str(item_root / "design" / "verification_responsibility_map.json"),
            "--testability-gate",
            str(item_root / "acceptance" / "testability_gate.json"),
            "--case-plan",
            str(item_root / "testcases" / "case_plan.json"),
        )
    ]


def _test_design_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return [
        _python(
            "skills/test-design/scripts/validate_test_design_matrix.py",
            "--input",
            str(item_root / "design" / "test_design_matrix.json"),
            "--testability-gate",
            str(item_root / "acceptance" / "testability_gate.json"),
            "--acceptance-examples",
            str(item_root / "acceptance" / "acceptance_examples.json"),
            "--responsibility-map",
            str(item_root / "design" / "verification_responsibility_map.json"),
            "--case-plan",
            str(item_root / "testcases" / "case_plan.json"),
        )
    ]


def _case_plan_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    level = work_item_level.upper()
    command = _python(
        "skills/case-generation/scripts/validate_case_plan.py",
        "--input",
        str(item_root / "testcases" / "case_plan.json"),
        "--testability-gate",
        str(item_root / "acceptance" / "testability_gate.json"),
    )
    if level in {"M", "L"}:
        command.extend(
            [
                "--acceptance-examples",
                str(item_root / "acceptance" / "acceptance_examples.json"),
                "--require-examples",
            ]
        )
    if level == "L":
        command.extend(
            [
                "--responsibility-map",
                str(item_root / "design" / "verification_responsibility_map.json"),
                "--require-responsibilities",
            ]
        )
    return [command]


def _testcase_commands(
    item_root: Path,
    _project_code: str,
    _work_item_id: str,
    work_item_level: str,
    strict: bool,
) -> list[list[str]]:
    level = work_item_level.upper()
    testcases = item_root / "testcases" / "testcases_main.md"
    commands = [
        _python(
            "skills/case-generation/scripts/testcase_lint.py",
            "--input",
            str(testcases),
        ),
        _python(
            "skills/case-generation/scripts/validate_testcase_grouping.py",
            "--input",
            str(testcases),
            *(["--strict"] if strict else []),
        ),
        _python(
            "skills/case-generation/scripts/validate_testpoints_view.py",
            "--input",
            str(item_root / "testcases" / "testpoints.json"),
            "--case-plan",
            str(item_root / "testcases" / "case_plan.json"),
            "--testability-gate",
            str(item_root / "acceptance" / "testability_gate.json"),
            *(["--strict"] if strict else []),
        ),
    ]
    case_plan_command = _python(
        "skills/case-generation/scripts/validate_case_plan.py",
        "--input",
        str(item_root / "testcases" / "case_plan.json"),
        "--testability-gate",
        str(item_root / "acceptance" / "testability_gate.json"),
        "--testcases",
        str(testcases),
    )
    if level in {"M", "L"}:
        case_plan_command.extend(
            [
                "--acceptance-examples",
                str(item_root / "acceptance" / "acceptance_examples.json"),
                "--require-examples",
            ]
        )
    if level == "L":
        case_plan_command.extend(
            [
                "--responsibility-map",
                str(item_root / "design" / "verification_responsibility_map.json"),
                "--require-responsibilities",
            ]
        )
    commands.append(case_plan_command)
    return commands


def _traceability_commands(
    item_root: Path,
    project_code: str,
    work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    commands = []
    bundle = item_root / "testcases" / "testcase_bundle.json"
    if bundle.exists():
        commands.append(
            _python(
                "scripts/validate_testcase_bundle.py",
                "--input",
                str(bundle),
                "--testcases",
                str(item_root / "testcases" / "testcases_main.md"),
                "--case-plan",
                str(item_root / "testcases" / "case_plan.json"),
                "--project-code",
                project_code,
                "--work-item-id",
                work_item_id,
            )
        )
    command = _python(
        "scripts/validate_traceability_assets.py",
        "--evidence",
        str(item_root / "evidence" / "evidence_inventory.json"),
        "--structured-prd",
        str(item_root / "structured_prd" / "structured_prd.json"),
        "--testcases",
        str(item_root / "testcases" / "testcases_main.md"),
        "--coverage-matrix",
        str(item_root / "coverage" / "coverage_matrix.json"),
        "--coverage-first-traceability",
        str(item_root / "traceability" / "coverage_first_traceability.json"),
        "--primary-only",
    )
    adapter = item_root / "traceability" / "traceability_adapter.json"
    if adapter.exists():
        command.extend(["--traceability-adapter", str(adapter)])
    commands.append(command)
    return commands


def _strict_gate_commands(
    _item_root: Path,
    project_code: str,
    work_item_id: str,
    _work_item_level: str,
    strict: bool,
) -> list[list[str]]:
    command = _python(
        "scripts/validate_work_item.py",
        "--project-code",
        project_code,
        "--work-item-id",
        work_item_id,
        "--skip-code-reviews",
        "--retention",
        "auto",
    )
    if strict:
        command.append("--strict")
    return [command]


ALL_LEVELS = frozenset({"S", "M", "L"})
ML_LEVELS = frozenset({"M", "L"})
L_LEVEL = frozenset({"L"})

STAGES = (
    StageSpec(
        "requirement_intake",
        "validation",
        ALL_LEVELS,
        ("inputs/requirement_summary.md", "inputs/source_manifest.json"),
        _requirement_commands,
    ),
    StageSpec(
        "evidence",
        "checkpoint",
        ALL_LEVELS,
        ("evidence/evidence_inventory.json",),
        _no_commands,
    ),
    StageSpec(
        "reasoning",
        "checkpoint",
        ALL_LEVELS,
        ("analysis/reasoning_pack.json",),
        _no_commands,
    ),
    StageSpec(
        "structured_prd",
        "validation",
        ALL_LEVELS,
        ("structured_prd/structured_prd.json",),
        _structured_prd_commands,
    ),
    StageSpec(
        "coverage",
        "validation",
        ALL_LEVELS,
        ("coverage/coverage_matrix.json",),
        _coverage_commands,
    ),
    StageSpec(
        "testability_gate",
        "validation",
        ALL_LEVELS,
        ("acceptance/testability_gate.json",),
        _testability_commands,
    ),
    StageSpec(
        "acceptance_examples",
        "validation",
        ML_LEVELS,
        ("acceptance/acceptance_examples.json",),
        _acceptance_commands,
    ),
    StageSpec(
        "verification_responsibility_map",
        "validation",
        L_LEVEL,
        ("design/verification_responsibility_map.json",),
        _responsibility_commands,
    ),
    StageSpec(
        "test_design_matrix",
        "validation",
        L_LEVEL,
        ("design/test_design_matrix.json",),
        _test_design_commands,
    ),
    StageSpec(
        "case_plan",
        "validation",
        ALL_LEVELS,
        ("testcases/case_plan.json",),
        _case_plan_commands,
    ),
    StageSpec(
        "testcases",
        "validation",
        ALL_LEVELS,
        (
            "testcases/testcases_main.md",
            "testcases/testpoints.json",
        ),
        _testcase_commands,
    ),
    StageSpec(
        "traceability",
        "validation",
        ALL_LEVELS,
        ("traceability/coverage_first_traceability.json",),
        _traceability_commands,
    ),
    StageSpec(
        "review",
        "checkpoint",
        ALL_LEVELS,
        ("reviews/review_record.md", "reviews/quality_report.json"),
        _no_commands,
    ),
    StageSpec(
        "strict_gate",
        "gate",
        ALL_LEVELS,
        ("manifest.json",),
        _strict_gate_commands,
    ),
)


def resolve_stage_plan(level: str) -> list[StageSpec]:
    normalized = level.strip().upper()
    if normalized not in ALL_LEVELS:
        raise ValueError(f"work_item_level 必须是 S/M/L，实际: {level}")
    return [stage for stage in STAGES if normalized in stage.levels]


def stage_ids(level: str) -> list[str]:
    return [stage.stage_id for stage in resolve_stage_plan(level)]

