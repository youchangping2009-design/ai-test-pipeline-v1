#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
review_gate.py

用途：
将 AI Test Pipeline 的关键质量检查串成统一 Gate。

当前 Gate 包含：
0. evidence_inventory / traceability_matrix 校验
   - schema 校验
   - 证据、结构化产物与 testcase 追踪关系校验
1. structured_prd JSON 校验
   - schema 校验
   - Flow 业务规则校验
2. testcase Markdown 校验
   - 表结构校验
   - 通用质量校验
   - 标签/编号/测试类型校验
   - Flow 流程类用例校验
3. review checklist 文件存在性与关键章节检查

适用场景：
- 本地自检
- MR 前质量门
- 后续 CI 集成

推荐用法：
python skills/review-gate/scripts/review_gate.py \
  --structured-prd assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md \
  --checklist skills/review-gate/checklists/manual_review_checklist.md

也可仅校验某一部分：
python skills/review-gate/scripts/review_gate.py \
  --structured-prd assets/projects/WX-YYPT/work_items/REQ-001/structured_prd/structured_prd.json

python skills/review-gate/scripts/review_gate.py \
  --testcases assets/projects/WX-YYPT/work_items/REQ-001/testcases/testcases_main.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.backend_config_utils import has_backend_config_family_pages

try:
    from jsonschema import Draft7Validator
except ImportError:
    Draft7Validator = None


# =========================
# 通用工具
# =========================

def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def should_run_backend_config_chain(image_evidence_path: Path) -> bool:
    if not image_evidence_path.exists():
        return False
    try:
        return has_backend_config_family_pages(load_json(image_evidence_path))
    except Exception:
        return False


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def format_json_path(error_path: List[Any]) -> str:
    if not error_path:
        return "$"
    result = "$"
    for item in error_path:
        if isinstance(item, int):
            result += f"[{item}]"
        else:
            result += f".{item}"
    return result


def get_repo_root() -> Path:
    """
    当前脚本路径预期为：
    skills/review-gate/scripts/review_gate.py
    """
    return Path(__file__).resolve().parents[3]


def resolve_schema_path(user_schema: str | None) -> Path:
    if user_schema:
        return Path(user_schema).resolve()

    repo_root = get_repo_root()
    primary = repo_root / "schemas" / "structured_prd.schema.json"
    if primary.exists():
        return primary

    fallback = (
        repo_root
        / "skills"
        / "prd-structuring"
        / "schema"
        / "structured_prd.schema.json"
    )
    return fallback


# =========================
# structured_prd 校验
# =========================

def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    if Draft7Validator is None:
        return []

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    messages: List[str] = []
    for err in errors:
        path = format_json_path(list(err.path))
        messages.append(f"[Schema校验失败] {path}: {err.message}")
    return messages


def build_module_feature_index(data: Dict[str, Any]) -> Tuple[set[str], set[tuple[str, str]]]:
    module_names: set[str] = set()
    module_feature_pairs: set[tuple[str, str]] = set()

    modules = data.get("modules", [])
    if not isinstance(modules, list):
        return module_names, module_feature_pairs

    for module in modules:
        if not isinstance(module, dict):
            continue

        module_name = module.get("module_name")
        if isinstance(module_name, str) and module_name.strip():
            module_names.add(module_name.strip())

        features = module.get("features", [])
        if not isinstance(features, list):
            continue

        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_name = feature.get("feature_name")
            if (
                isinstance(module_name, str)
                and module_name.strip()
                and isinstance(feature_name, str)
                and feature_name.strip()
            ):
                module_feature_pairs.add((module_name.strip(), feature_name.strip()))

    return module_names, module_feature_pairs


def validate_flows_business_rules(data: Dict[str, Any]) -> List[str]:
    """
    Flow 层额外业务校验：
    - flow_id 唯一
    - steps 非空
    - step_no 连续递增
    - step 的 module_name / feature_name 可映射回 modules
    - is_key_checkpoint=true 时 checkpoints 不为空
    - state_transition 的 from/to 完整性
    - related_modules 与 steps 中 module_name 一致性
    - main_flow 必须具备 success_criteria / priority / tags
    """
    messages: List[str] = []

    module_names, module_feature_pairs = build_module_feature_index(data)
    flows = data.get("flows", [])

    if not isinstance(flows, list):
        messages.append("[业务校验失败] $.flows: flows 必须为数组")
        return messages

    flow_ids_seen: set[str] = set()

    for flow_idx, flow in enumerate(flows):
        base_path = f"$.flows[{flow_idx}]"

        if not isinstance(flow, dict):
            messages.append(f"[业务校验失败] {base_path}: flow 必须为对象")
            continue

        flow_id = flow.get("flow_id")
        if isinstance(flow_id, str) and flow_id.strip():
            if flow_id in flow_ids_seen:
                messages.append(f"[业务校验失败] {base_path}.flow_id: flow_id 重复: {flow_id}")
            flow_ids_seen.add(flow_id)
        else:
            messages.append(f"[业务校验失败] {base_path}.flow_id: flow_id 不能为空")

        steps = flow.get("steps", [])
        if not isinstance(steps, list) or not steps:
            messages.append(f"[业务校验失败] {base_path}.steps: steps 必须为非空数组")
            continue

        # step_no 连续性
        actual_step_nos: List[int] = []
        for step_idx, step in enumerate(steps):
            step_path = f"{base_path}.steps[{step_idx}]"
            if not isinstance(step, dict):
                messages.append(f"[业务校验失败] {step_path}: step 必须为对象")
                continue

            step_no = step.get("step_no")
            if not isinstance(step_no, int):
                messages.append(f"[业务校验失败] {step_path}.step_no: step_no 必须为整数")
                continue
            actual_step_nos.append(step_no)

        expected_step_nos = list(range(1, len(steps) + 1))
        if actual_step_nos != expected_step_nos:
            messages.append(
                f"[业务校验失败] {base_path}.steps.step_no: "
                f"step_no 必须从 1 开始连续递增，当前为 {actual_step_nos}，期望为 {expected_step_nos}"
            )

        # step 级映射校验
        step_modules: set[str] = set()

        for step_idx, step in enumerate(steps):
            step_path = f"{base_path}.steps[{step_idx}]"
            if not isinstance(step, dict):
                continue

            module_name = step.get("module_name")
            feature_name = step.get("feature_name")
            checkpoints = step.get("checkpoints")
            is_key_checkpoint = step.get("is_key_checkpoint")

            if isinstance(module_name, str) and module_name.strip():
                step_modules.add(module_name.strip())
                if module_name.strip() not in module_names:
                    messages.append(
                        f"[业务校验失败] {step_path}.module_name: "
                        f"未在 modules 中找到对应 module_name: {module_name}"
                    )
            else:
                messages.append(f"[业务校验失败] {step_path}.module_name: module_name 不能为空")

            if (
                isinstance(module_name, str)
                and module_name.strip()
                and isinstance(feature_name, str)
                and feature_name.strip()
            ):
                if (module_name.strip(), feature_name.strip()) not in module_feature_pairs:
                    messages.append(
                        f"[业务校验失败] {step_path}.feature_name: "
                        f"未在 modules 中找到对应 feature_name: "
                        f"module_name={module_name}, feature_name={feature_name}"
                    )
            else:
                messages.append(f"[业务校验失败] {step_path}.feature_name: feature_name 不能为空")

            if is_key_checkpoint is True:
                if not isinstance(checkpoints, list) or len(checkpoints) == 0:
                    messages.append(
                        f"[业务校验失败] {step_path}.checkpoints: "
                        "is_key_checkpoint=true 时，checkpoints 不能为空"
                    )

            state_transition = step.get("state_transition")
            if state_transition is not None:
                if not isinstance(state_transition, dict):
                    messages.append(
                        f"[业务校验失败] {step_path}.state_transition: state_transition 必须为对象"
                    )
                else:
                    from_state = state_transition.get("from")
                    to_state = state_transition.get("to")
                    has_from = isinstance(from_state, str) and from_state.strip() != ""
                    has_to = isinstance(to_state, str) and to_state.strip() != ""
                    if has_from != has_to:
                        messages.append(
                            f"[业务校验失败] {step_path}.state_transition: "
                            "from 和 to 必须同时填写，或同时不填写"
                        )

        related_modules = flow.get("related_modules")
        if related_modules is not None:
            if not isinstance(related_modules, list):
                messages.append(
                    f"[业务校验失败] {base_path}.related_modules: related_modules 必须为数组"
                )
            else:
                related_set = {
                    item.strip()
                    for item in related_modules
                    if isinstance(item, str) and item.strip()
                }
                if step_modules and related_set and step_modules != related_set:
                    messages.append(
                        f"[业务校验失败] {base_path}.related_modules: "
                        f"related_modules 与 steps 中实际引用模块不一致。"
                        f"steps={sorted(step_modules)}, related_modules={sorted(related_set)}"
                    )

        flow_type = flow.get("flow_type")
        success_criteria = flow.get("success_criteria")
        priority = flow.get("priority")
        tags = flow.get("tags")

        if flow_type == "main_flow":
            if not isinstance(success_criteria, list) or len(success_criteria) == 0:
                messages.append(
                    f"[业务校验失败] {base_path}.success_criteria: "
                    "main_flow 必须定义 success_criteria"
                )
            if not isinstance(priority, str) or not priority.strip():
                messages.append(
                    f"[业务校验失败] {base_path}.priority: "
                    "main_flow 必须定义 priority"
                )
            if not isinstance(tags, list) or len(tags) == 0:
                messages.append(
                    f"[业务校验失败] {base_path}.tags: "
                    "main_flow 至少包含一个标签"
                )

    return messages


def run_structured_prd_gate(
    repo_root: Path,
    structured_prd_path: Path,
    schema_path: Path,
) -> Tuple[bool, List[str]]:
    """
    直接复用现有 validate_structured_prd.py，避免在 review_gate 中重复维护
    structured_prd schema 与 Flow 业务规则。
    """
    script_path = repo_root / "skills" / "prd-structuring" / "scripts" / "validate_structured_prd.py"
    if not script_path.exists():
        return False, [f"structured_prd 校验脚本不存在: {script_path}"]

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(structured_prd_path),
        "--schema",
        str(schema_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr

    if result.returncode == 0:
        return True, []

    lines = [line for line in output.splitlines() if line.strip()]
    return False, lines


def run_traceability_gate(
    repo_root: Path,
    evidence_path: Path,
    traceability_path: Path,
    structured_prd_path: Path,
    testcase_path: Path,
) -> Tuple[bool, List[str]]:
    import subprocess

    script_path = repo_root / "scripts" / "validate_traceability_assets.py"
    if not script_path.exists():
        return False, [f"traceability 校验脚本不存在: {script_path}"]

    command = [
        sys.executable,
        str(script_path),
        "--evidence",
        str(evidence_path),
        "--traceability",
        str(traceability_path),
        "--structured-prd",
        str(structured_prd_path),
        "--testcases",
        str(testcase_path),
    ]

    traceability_dir = traceability_path.parent
    coverage_first_path = traceability_dir / "coverage_first_traceability.json"
    traceability_adapter_path = traceability_dir / "traceability_adapter.json"
    coverage_matrix_path = traceability_dir.parent / "coverage" / "coverage_matrix.json"
    if coverage_matrix_path.exists():
        command.extend(["--coverage-matrix", str(coverage_matrix_path)])
    if coverage_first_path.exists():
        command.extend(["--coverage-first-traceability", str(coverage_first_path)])
    if traceability_adapter_path.exists():
        command.extend(["--traceability-adapter", str(traceability_adapter_path)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr

    if result.returncode == 0:
        return True, []

    return False, [line for line in output.splitlines() if line.strip()]


def run_backend_config_chain_gate(
    repo_root: Path,
    image_evidence_path: Path,
    evidence_path: Path,
    structured_prd_path: Path,
    testcase_path: Path,
) -> Tuple[bool, List[str]]:
    import subprocess

    script_path = repo_root / "scripts" / "validate_backend_config_chain.py"
    if not script_path.exists():
        return False, [f"后台配置页链路校验脚本不存在: {script_path}"]

    command = [
        sys.executable,
        str(script_path),
        "--image-evidence",
        str(image_evidence_path),
        "--evidence",
        str(evidence_path),
        "--structured-prd",
        str(structured_prd_path),
        "--testcases",
        str(testcase_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr

    if result.returncode == 0:
        return True, []

    return False, [line for line in output.splitlines() if line.strip()]


# =========================
# testcase lint（调用现有脚本）
# =========================

def run_testcase_gate(repo_root: Path, testcase_path: Path) -> Tuple[bool, List[str]]:
    """
    直接调用现有 testcase_lint.py，避免在 review_gate 中重复维护一套规则。
    """
    import subprocess

    script_path = repo_root / "skills" / "case-generation" / "scripts" / "testcase_lint.py"
    if not script_path.exists():
        return False, [f"testcase lint 脚本不存在: {script_path}"]

    command = [
        sys.executable,
        str(script_path),
        "--input",
        str(testcase_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        if output:
            output += "\n"
        output += result.stderr

    if result.returncode == 0:
        return True, []

    # 将脚本输出按行拆回 review_gate 的错误列表
    lines = [line for line in output.splitlines() if line.strip()]
    return False, lines


# =========================
# checklist 检查（对齐新版 checklist）
# =========================

def run_checklist_gate(checklist_path: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not checklist_path.exists():
        errors.append(f"checklist 文件不存在: {checklist_path}")
        return False, errors

    try:
        content = read_text(checklist_path)
    except Exception as exc:
        return False, [f"读取 checklist 文件失败: {exc}"]

    required_keywords = [
        "Flow 结构评审",
        "用例组织方式评审",
        "编号 / 标签 / 优先级 / 测试类型评审",
        "评审投入识别",
    ]

    for keyword in required_keywords:
        if keyword not in content:
            errors.append(f"checklist 缺少关键评审章节: {keyword}")

    return len(errors) == 0, errors


# =========================
# 汇总 Gate
# =========================

def main() -> int:
    parser = argparse.ArgumentParser(description="统一执行 AI Test Pipeline Review Gate")
    parser.add_argument(
        "--image-evidence",
        required=False,
        help="image_evidence_inventory JSON 文件路径",
    )
    parser.add_argument(
        "--evidence",
        required=False,
        help="evidence_inventory JSON 文件路径",
    )
    parser.add_argument(
        "--structured-prd",
        required=False,
        help="structured_prd JSON 文件路径",
    )
    parser.add_argument(
        "--traceability",
        required=False,
        help="traceability_matrix JSON 文件路径",
    )
    parser.add_argument(
        "--schema",
        required=False,
        help="structured_prd schema 路径；不传则默认优先 schemas/structured_prd.schema.json",
    )
    parser.add_argument(
        "--testcases",
        required=False,
        help="Markdown 测试用例文件路径",
    )
    parser.add_argument(
        "--checklist",
        required=False,
        help="人工评审清单文件路径",
    )
    args = parser.parse_args()

    if not args.image_evidence and not args.evidence and not args.structured_prd and not args.traceability and not args.testcases and not args.checklist:
        print("请至少传入一个校验对象：--image-evidence / --evidence / --structured-prd / --traceability / --testcases / --checklist", file=sys.stderr)
        return 1

    overall_pass = True
    summary: List[str] = []
    repo_root = get_repo_root()

    if args.evidence or args.traceability:
        if not (args.evidence and args.traceability and args.structured_prd and args.testcases):
            print("执行 traceability gate 时，必须同时传入 --evidence --traceability --structured-prd --testcases", file=sys.stderr)
            return 1

        evidence_path = Path(args.evidence).resolve()
        traceability_path = Path(args.traceability).resolve()
        structured_prd_path = Path(args.structured_prd).resolve()
        testcase_path = Path(args.testcases).resolve()

        print_section("Traceability Gate")
        print(f"Evidence文件: {evidence_path}")
        print(f"Traceability文件: {traceability_path}")
        print(f"Structured PRD文件: {structured_prd_path}")
        print(f"Testcase文件: {testcase_path}")

        ok, errors = run_traceability_gate(
            repo_root=repo_root,
            evidence_path=evidence_path,
            traceability_path=traceability_path,
            structured_prd_path=structured_prd_path,
            testcase_path=testcase_path,
        )
        if ok:
            print("✅ Traceability 校验通过")
            summary.append("Traceability: PASS")
        else:
            overall_pass = False
            print("❌ Traceability 校验失败")
            for err in errors:
                print(err)
            summary.append(f"Traceability: FAIL ({len(errors)} 行输出)")

        if args.image_evidence:
            image_evidence_path = Path(args.image_evidence).resolve()
            if should_run_backend_config_chain(image_evidence_path):
                print_section("Backend Config Chain Gate")
                print(f"Image Evidence文件: {image_evidence_path}")
                ok, errors = run_backend_config_chain_gate(
                    repo_root=repo_root,
                    image_evidence_path=image_evidence_path,
                    evidence_path=evidence_path,
                    structured_prd_path=structured_prd_path,
                    testcase_path=testcase_path,
                )
                if ok:
                    print("✅ 后台配置页链路校验通过")
                    summary.append("Backend Config Chain: PASS")
                else:
                    overall_pass = False
                    print("❌ 后台配置页链路校验失败")
                    for err in errors:
                        print(err)
                    summary.append(f"Backend Config Chain: FAIL ({len(errors)} 行输出)")

    if args.structured_prd:
        structured_prd_path = Path(args.structured_prd).resolve()
        schema_path = resolve_schema_path(args.schema)

        print_section("Structured PRD Gate")
        print(f"输入文件: {structured_prd_path}")
        print(f"Schema文件: {schema_path}")

        ok, errors = run_structured_prd_gate(repo_root, structured_prd_path, schema_path)
        if ok:
            print("✅ Structured PRD 校验通过")
            summary.append("Structured PRD: PASS")
        else:
            overall_pass = False
            print("❌ Structured PRD 校验失败")
            for err in errors:
                print(err)
            summary.append(f"Structured PRD: FAIL ({len(errors)} 个问题)")

    if args.testcases:
        testcase_path = Path(args.testcases).resolve()

        print_section("Testcase Gate")
        print(f"输入文件: {testcase_path}")

        ok, errors = run_testcase_gate(repo_root, testcase_path)
        if ok:
            print("✅ Testcase 校验通过")
            summary.append("Testcases: PASS")
        else:
            overall_pass = False
            print("❌ Testcase 校验失败")
            for err in errors:
                print(err)
            summary.append(f"Testcases: FAIL ({len(errors)} 行输出)")

    if args.checklist:
        checklist_path = Path(args.checklist).resolve()

        print_section("Checklist Gate")
        print(f"输入文件: {checklist_path}")

        ok, errors = run_checklist_gate(checklist_path)
        if ok:
            print("✅ Checklist 检查通过")
            summary.append("Checklist: PASS")
        else:
            overall_pass = False
            print("❌ Checklist 检查失败")
            for err in errors:
                print(err)
            summary.append(f"Checklist: FAIL ({len(errors)} 个问题)")

    print_section("Review Gate Summary")
    for item in summary:
        print(f"- {item}")

    if overall_pass:
        print("\n🎉 Review Gate 通过")
        return 0

    print("\n🚫 Review Gate 未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
