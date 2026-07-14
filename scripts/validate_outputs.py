#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate_outputs.py

用途：
作为项目级统一校验入口，串联以下质量检查：

1. structured_prd 校验
   - schema 校验
   - Flow 业务规则校验

2. testcase 校验
   - Markdown 表格结构校验
   - 通用质量校验
   - 标签 / 编号 / 测试类型校验
   - Flow 流程类用例 lint

3. review_gate 校验
   - checklist 文件存在性与关键章节检查
   - 统一 Gate 汇总

适用场景：
- 本地项目级自检
- MR 提交前检查
- 后续 CI 集成

推荐用法：

方式一：按项目编码自动推断路径
python scripts/validate_outputs.py --project-code WX-YYPT

方式二：显式传入文件路径
python scripts/validate_outputs.py \
  --structured-prd assets/projects/WX-YYPT/structured_prd/structured_prd.json \
  --testcases assets/projects/WX-YYPT/testcases/testcases_main.md \
  --checklist skills/review-gate/checklists/manual_review_checklist.md

方式三：只校验部分内容
python scripts/validate_outputs.py --project-code WX-YYPT --skip-testcases
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def get_repo_root() -> Path:
    """
    当前脚本路径预期为：
    scripts/validate_outputs.py
    """
    return Path(__file__).resolve().parents[1]


def resolve_project_root(repo_root: Path, project_code: str) -> Path:
    return repo_root / "assets" / "projects" / project_code


def find_first_json_file(directory: Path) -> Optional[Path]:
    if not directory.exists() or not directory.is_dir():
        return None

    candidates = sorted(directory.glob("*.json"))
    if not candidates:
        return None

    preferred_names = [
        "structured_prd.json",
        "output.json",
        "demo.json",
    ]
    for name in preferred_names:
        for candidate in candidates:
            if candidate.name == name:
                return candidate

    return candidates[0]


def find_first_md_file(directory: Path) -> Optional[Path]:
    if not directory.exists() or not directory.is_dir():
        return None

    candidates = sorted(directory.glob("*.md"))
    if not candidates:
        return None

    preferred_names = [
        "testcases.md",
        "output.md",
        "demo.md",
    ]
    for name in preferred_names:
        for candidate in candidates:
            if candidate.name == name:
                return candidate

    return candidates[0]


def resolve_default_paths(
    repo_root: Path,
    project_code: str,
) -> Tuple[Optional[Path], Optional[Path], Path]:
    project_root = resolve_project_root(repo_root, project_code)
    structured_prd_dir = project_root / "structured_prd"
    testcases_dir = project_root / "testcases"
    checklist_path = repo_root / "skills" / "review-gate" / "checklists" / "manual_review_checklist.md"

    structured_prd_path = find_first_json_file(structured_prd_dir)
    testcase_path = find_first_md_file(testcases_dir)

    return structured_prd_path, testcase_path, checklist_path


def run_subprocess(command: List[str]) -> Tuple[int, str]:
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
    return result.returncode, output.strip()


def validate_structured_prd(
    repo_root: Path,
    structured_prd_path: Path,
    schema_path: Optional[Path],
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "prd-structuring" / "scripts" / "validate_structured_prd.py"

    if not script_path.exists():
        return False, f"structured_prd 校验脚本不存在: {script_path}"

    command = [sys.executable, str(script_path), "--input", str(structured_prd_path)]
    if schema_path:
        command.extend(["--schema", str(schema_path)])

    code, output = run_subprocess(command)
    return code == 0, output


def validate_testcases(
    repo_root: Path,
    testcase_path: Path,
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "case-generation" / "scripts" / "testcase_lint.py"

    if not script_path.exists():
        return False, f"testcase lint 脚本不存在: {script_path}"

    command = [sys.executable, str(script_path), "--input", str(testcase_path)]
    code, output = run_subprocess(command)
    return code == 0, output


def validate_review_gate(
    repo_root: Path,
    structured_prd_path: Optional[Path],
    schema_path: Optional[Path],
    testcase_path: Optional[Path],
    checklist_path: Optional[Path],
) -> Tuple[bool, str]:
    script_path = repo_root / "skills" / "review-gate" / "scripts" / "review_gate.py"

    if not script_path.exists():
        return False, f"review_gate 脚本不存在: {script_path}"

    command = [sys.executable, str(script_path)]

    if structured_prd_path:
        command.extend(["--structured-prd", str(structured_prd_path)])
    if schema_path:
        command.extend(["--schema", str(schema_path)])
    if testcase_path:
        command.extend(["--testcases", str(testcase_path)])
    if checklist_path:
        command.extend(["--checklist", str(checklist_path)])

    code, output = run_subprocess(command)
    return code == 0, output


def should_run_review_gate(args: argparse.Namespace) -> Tuple[bool, str]:
    if args.skip_review_gate:
        return False, "用户显式跳过 review_gate"
    if args.skip_structured_prd:
        return False, "已跳过 structured_prd，review_gate 同步跳过"
    if args.skip_testcases:
        return False, "已跳过 testcases，review_gate 同步跳过"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Test Pipeline 项目级统一输出校验入口")
    parser.add_argument(
        "--project-code",
        required=False,
        help="项目编码，如 WX-YYPT；用于自动推断 assets/projects/<project_code>/ 下的文件路径",
    )
    parser.add_argument(
        "--structured-prd",
        required=False,
        help="显式指定 structured_prd JSON 文件路径",
    )
    parser.add_argument(
        "--testcases",
        required=False,
        help="显式指定测试用例 Markdown 文件路径",
    )
    parser.add_argument(
        "--checklist",
        required=False,
        help="显式指定人工评审清单文件路径",
    )
    parser.add_argument(
        "--schema",
        required=False,
        help="显式指定 structured_prd schema 路径",
    )
    parser.add_argument(
        "--skip-structured-prd",
        action="store_true",
        help="跳过 structured_prd 校验",
    )
    parser.add_argument(
        "--skip-testcases",
        action="store_true",
        help="跳过 testcase 校验",
    )
    parser.add_argument(
        "--skip-review-gate",
        action="store_true",
        help="跳过 review_gate 统一校验",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()

    structured_prd_path: Optional[Path] = Path(args.structured_prd).resolve() if args.structured_prd else None
    testcase_path: Optional[Path] = Path(args.testcases).resolve() if args.testcases else None
    checklist_path: Optional[Path] = Path(args.checklist).resolve() if args.checklist else None
    schema_path: Optional[Path] = Path(args.schema).resolve() if args.schema else None

    if args.project_code:
        default_structured_prd, default_testcase, default_checklist = resolve_default_paths(
            repo_root, args.project_code
        )
        if structured_prd_path is None:
            structured_prd_path = default_structured_prd
        if testcase_path is None:
            testcase_path = default_testcase
        if checklist_path is None:
            checklist_path = default_checklist

    if not args.skip_structured_prd and not structured_prd_path:
        print("未找到 structured_prd 文件。请通过 --structured-prd 显式指定，或提供 --project-code。", file=sys.stderr)
        return 1

    if not args.skip_testcases and not testcase_path:
        print("未找到 testcase 文件。请通过 --testcases 显式指定，或提供 --project-code。", file=sys.stderr)
        return 1

    if not args.skip_review_gate and not checklist_path:
        print("未找到 checklist 文件。请通过 --checklist 显式指定，或提供 --project-code。", file=sys.stderr)
        return 1

    overall_pass = True
    summary: List[str] = []

    if not args.skip_structured_prd and structured_prd_path:
        print_section("Step 1 - Structured PRD Validation")
        print(f"structured_prd: {structured_prd_path}")
        if schema_path:
            print(f"schema: {schema_path}")

        ok, output = validate_structured_prd(repo_root, structured_prd_path, schema_path)
        print(output if output else "(无输出)")
        summary.append(f"Structured PRD: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    if not args.skip_testcases and testcase_path:
        print_section("Step 2 - Testcases Validation")
        print(f"testcases: {testcase_path}")

        ok, output = validate_testcases(repo_root, testcase_path)
        print(output if output else "(无输出)")
        summary.append(f"Testcases: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False

    run_review_gate, review_gate_skip_reason = should_run_review_gate(args)
    if run_review_gate:
        print_section("Step 3 - Review Gate Validation")
        if structured_prd_path:
            print(f"structured_prd: {structured_prd_path}")
        if testcase_path:
            print(f"testcases: {testcase_path}")
        if checklist_path:
            print(f"checklist: {checklist_path}")
        if schema_path:
            print(f"schema: {schema_path}")

        ok, output = validate_review_gate(
            repo_root=repo_root,
            structured_prd_path=structured_prd_path,
            schema_path=schema_path,
            testcase_path=testcase_path,
            checklist_path=checklist_path,
        )
        print(output if output else "(无输出)")
        summary.append(f"Review Gate: {'PASS' if ok else 'FAIL'}")
        if not ok:
            overall_pass = False
    else:
        print_section("Step 3 - Review Gate Validation")
        print(f"- 跳过 review_gate：{review_gate_skip_reason}")
        summary.append("Review Gate: SKIPPED")

    print_section("Validate Outputs Summary")
    for item in summary:
        print(f"- {item}")

    if overall_pass:
        print("\n🎉 项目输出校验通过")
        return 0

    print("\n🚫 项目输出校验未通过")
    return 1


if __name__ == "__main__":
    sys.exit(main())
