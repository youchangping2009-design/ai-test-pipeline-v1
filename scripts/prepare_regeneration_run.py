#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from backend_config_utils import has_backend_config_family_pages
from work_item_policy import VALID_WORK_ITEM_LEVELS
from work_item_policy import resolve_work_item_level


ROOT = Path(__file__).resolve().parents[1]
CURRENT_TASK_FILES = [
    "00-preflight.md",
    "00-requirement-intake.md",
    "01-reasoning-analyst.md",
    "02-prd-structurer.md",
    "03-coverage-planner.md",
    "03a-testability-gate.md",
    "03b-acceptance-examples.md",
    "03c-test-design.md",
    "03d-case-plan.md",
    "04-case-generator.md",
    "05-case-reviewer.md",
    "06-asset-formatter.md",
    "07-frontend-code-review.md",
    "08-backend-code-review.md",
]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def list_input_files(inputs_dir: Path) -> list[Path]:
    return sorted(
        [path for path in inputs_dir.rglob("*") if path.is_file()],
        key=lambda p: str(p.relative_to(inputs_dir)),
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def build_file_list(paths: Iterable[Path]) -> str:
    return "\n".join(f"- `{rel(path)}`" for path in paths)


def existing_paths(*paths: Path) -> list[Path]:
    return [path for path in paths if path.exists()]


def remove_stale_generation_files(generation_dir: Path) -> list[Path]:
    removed: list[Path] = []
    keep = set(CURRENT_TASK_FILES + ["run_manifest.json", "regeneration_bundle.json"])
    for path in generation_dir.glob("*.md"):
        if path.name in keep:
            continue
        path.unlink()
        removed.append(path)
    return removed


def should_run_backend_config_chain(image_evidence_path: Path) -> bool:
    if not image_evidence_path.exists():
        return False
    try:
        return has_backend_config_family_pages(read_json(image_evidence_path))
    except Exception:
        return False


def build_requirement_intake_task(
    generation_dir: Path,
    item_root: Path,
    manifest: dict,
    input_files: list[Path],
) -> None:
    references = [
        ROOT / "skills" / "requirement-summary" / "SKILL.md",
        ROOT / "skills" / "requirement-summary" / "references" / "output-contract.md",
        ROOT / "schemas" / "requirement_source_manifest.schema.json",
        ROOT / "scripts" / "validate_requirement_sources.py",
    ]
    content = f"""# Requirement Intake Run

- 工作项：`{manifest.get('work_item_id', '待确认')}`
- 标题：`{manifest.get('title', '待确认')}`
- 角色：`Requirement Summarizer`

## 输入
{build_file_list(input_files)}

## 参考规则
{build_file_list(references)}

## 产出目标
- `{rel(item_root / 'inputs' / 'requirement_summary.md')}`
- `{rel(item_root / 'inputs' / 'source_manifest.json')}`

## 强制要求
- 需求归一化是主流程第一阶段，不得跳过
- 必须保留原始 `inputs/`，不能用摘要替代原始资料
- `requirement_summary.md` 必须区分确认需求、风险、待确认问题和本轮边界
- `source_manifest.json` 必须记录所有实际消费来源及访问状态
- 本阶段不得生成 structured_prd、case_plan 或 testcase

## 校验命令
- `python3 scripts/validate_requirement_sources.py --input {rel(item_root / 'inputs' / 'source_manifest.json')} --strict`
"""
    write_text(generation_dir / "00-requirement-intake.md", content)


def build_reasoning_task(
    generation_dir: Path,
    item_root: Path,
    manifest: dict,
    input_files: list[Path],
) -> None:
    image_evidence_path = item_root / "image_evidence" / "image_evidence_inventory.json"
    outputs = [
        item_root / "analysis" / "analysis_report.md",
        item_root / "analysis" / "reasoning_pack.json",
    ]
    references = [
        ROOT / "prompts" / "prd_reasoning_prompt.md",
        ROOT / "schemas" / "reasoning_pack.schema.json",
        ROOT / "scripts" / "generate_reasoning_pack.py",
        ROOT / "scripts" / "validate_reasoning_pack.py",
    ]
    inputs_list = build_file_list(input_files)
    if image_evidence_path.exists():
        inputs_list = inputs_list + f"\n- `{rel(image_evidence_path)}`"

    content = f"""# Reasoning Analyst Run

- 工作项：`{manifest.get('work_item_id', '待确认')}`
- 标题：`{manifest.get('title', '待确认')}`
- 角色：`Reasoning Analyst`

## 输入
{inputs_list}

## 参考规则
{build_file_list(references)}

## 产出目标
{build_file_list(outputs)}

## 强制要求
- 必须优先消费 `inputs/` 与 `image_evidence/image_evidence_inventory.json`
- 不允许从既有 `structured_prd` 反推 reasoning
- 必须显式保留 AI 推理结果，不能只输出压缩后的结构化字段
- reasoning_pack 至少包含：
  - `requirement_summary`
  - `explicit_rules`
  - `implicit_rules`
  - `field_constraints`
  - `data_source_rules`
  - `business_risks`
  - `edge_cases`
  - `ambiguities`
  - `recommended_test_dimensions`
  - `coverage_candidates`
- `analysis_report.md` 负责可读摘要，`reasoning_pack.json` 负责机器可消费推理真源

## 校验命令
- `python3 scripts/generate_reasoning_pack.py --project-code {manifest.get('project_code', '待确认')} --work-item-id {manifest.get('work_item_id', '待确认')}`
- `python3 scripts/validate_reasoning_pack.py --input {rel(item_root / 'analysis' / 'reasoning_pack.json')} --schema schemas/reasoning_pack.schema.json`
"""
    write_text(generation_dir / "01-reasoning-analyst.md", content)


def build_structurer_task(
    generation_dir: Path,
    item_root: Path,
    manifest: dict,
    input_files: list[Path],
) -> None:
    image_evidence_path = item_root / "image_evidence" / "image_evidence_inventory.json"
    reasoning_pack_path = item_root / "analysis" / "reasoning_pack.json"
    outputs = []
    if image_evidence_path.exists():
        outputs.append(image_evidence_path)
    outputs.extend(
        [
            item_root / "evidence" / "evidence_inventory.json",
            item_root / "structured_prd" / "structured_prd.md",
            item_root / "structured_prd" / "structured_prd.json",
            item_root / "traceability" / "traceability_matrix.json",
        ]
    )
    references = [
        ROOT / "prompts" / "prd_input_prompt.md",
        ROOT / "prompts" / "prd_to_structured_prompt.md",
        ROOT / "scripts" / "compile_structured_prd_json.py",
        ROOT / "skills" / "prd-structuring" / "references" / "image_evidence_consumption.md",
        ROOT / "schemas" / "structured_prd.schema.json",
        ROOT / "AGENTS.md",
        ROOT / "WORKFLOW_CONTRACT.md",
    ]
    references.extend(
        existing_paths(
            ROOT / "tool_adapters" / "cursor" / "README.md",
        )
    )
    inputs_list = build_file_list(input_files)
    if image_evidence_path.exists():
        inputs_list = inputs_list + f"\n- `{rel(image_evidence_path)}`"
    if reasoning_pack_path.exists():
        inputs_list = inputs_list + f"\n- `{rel(reasoning_pack_path)}`"

    extra_requirements = ""
    extra_validation = ""
    if image_evidence_path.exists():
        extra_requirements = (
            "- 若输入主要是截图，先产出并校验 `image_evidence_inventory.json`\n"
            "- 先生成 `structured_prd.md`，再从 `structured_prd.md` 编译出 `structured_prd.json`\n"
            "- 生成 structured_prd 时必须优先消费 image evidence 的页面骨架、字段矩阵、说明表逐行规则、列表列头、操作入口和便签补充规则\n"
            "- 写出 structured_prd 与 testcase 后，执行字段属性同步与字段属性级 traceability 扩展"
        )
        extra_validation = (
            f"- `python3 skills/prd-image-evidence-extractor/scripts/validate_image_evidence.py --input {rel(image_evidence_path)}`\n"
            f"- `python3 scripts/validate_image_evidence_mapping.py --image-evidence {rel(image_evidence_path)} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')}`\n"
            f"- `python3 scripts/sync_modal_attributes_from_image_evidence.py --image-evidence {rel(image_evidence_path)} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')} --write`\n"
            f"- `python3 scripts/expand_backend_field_traceability.py --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')} --traceability {rel(item_root / 'traceability' / 'traceability_matrix.json')} --write`"
        )

    content = f"""# PRD Structurer Run

- 工作项：`{manifest.get('work_item_id', '待确认')}`
- 标题：`{manifest.get('title', '待确认')}`
- 角色：`PRD Structurer`

## 输入
{inputs_list}

## 参考规则
{build_file_list(references)}

## 产出目标
{build_file_list(outputs)}

## 强制要求
- 先整理输入，再生成 `structured_prd.md`
- 必须再从 `structured_prd.md` 编译出 `structured_prd.json`
- 必须显式消费 `analysis/reasoning_pack.json` 中的 `explicit_rules / implicit_rules / field_constraints / data_source_rules`
- 显式规则优先于视觉推断
- 对组合型说明做原子化拆解
- 对高优先级显式规则补充 `explicit_rules`，必要时补 `fidelity_points`
- 固定文案、样式差异、容器结果、默认状态、扩展性说明不得静默丢失
- 对“触发动作 -> 容器出现 -> 默认状态 / 终态结果”必须拆出中间检查点
- `evidence -> structured_prd -> traceability` 必须可追溯
- 对后台配置页字段矩阵，优先输出 `fields[]`，`field_definitions` 作为兼容层保留
- 对字段级规则，优先输出对象版 `rules[]`，不要只在 `field_rules.rule_text` 中保留自然语言
- `required_when` 必须显式落到字段与规则层，不能只用 `required=true + visible_when` 代替
- `data_source_constraint` 只保留真正影响候选项、筛选、排序的数据规则
- 条件展示 / 条件必填 / 条件只读或可编辑 / 数值边界 / 数据源过滤 / 数据源排序，必须进入机器可解析字段：
  - `required_when / visible_when / editable_when / readonly_when`
  - `min / max / integer_only / max_length / max_count`
  - `data_source / filter / display / order_by`
{extra_requirements}

## 校验命令
- `python3 scripts/project_reasoning_to_structured_prd.py --project-code {manifest.get('project_code', '待确认')} --work-item-id {manifest.get('work_item_id', '待确认')}`
- `python3 scripts/compile_structured_prd_json.py --input {rel(item_root / 'structured_prd' / 'structured_prd.md')} --output {rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `python3 skills/prd-structuring/scripts/validate_structured_prd.py --input {rel(item_root / 'structured_prd' / 'structured_prd.json')} --schema schemas/structured_prd.schema.json`
{extra_validation}
"""
    write_text(generation_dir / "02-prd-structurer.md", content)


def build_coverage_planner_task(generation_dir: Path, item_root: Path) -> None:
    references = [
        ROOT / "docs" / "testcase_signal_policy.md",
        ROOT / "schemas" / "coverage_matrix.schema.json",
        ROOT / "scripts" / "generate_coverage_matrix.py",
        ROOT / "scripts" / "validate_coverage_matrix.py",
    ]
    content = f"""# Coverage Planner Run

- 角色：`Coverage Planner`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'analysis' / 'reasoning_pack.json')}`

## 参考规则
{build_file_list(references)}

## 产出目标
- `{rel(item_root / 'coverage' / 'coverage_matrix.json')}`

## 强制要求
- 后续 `coverage_level / emit_mode` 分层必须以 `docs/testcase_signal_policy.md` 为统一口径
- coverage 不仅来自字段与规则机械展开
- 必须消费 reasoning_pack 中的：
  - `edge_cases`
  - `business_risks`
  - `recommended_test_dimensions`
- coverage_type 至少支持：
  - `field_property`
  - `required`
  - `conditional_required`
  - `conditional_visibility`
  - `conditional_editability`
  - `value_boundary`
  - `invalid_input`
  - `data_source_filter`
  - `data_source_display`
  - `data_source_order`
  - `happy_path_combo`
- 必须区分：
  - `source_origin=explicit_rule`
  - `source_origin=ai_reasoning`

## 校验命令
- `python3 scripts/generate_coverage_matrix.py --project-code {item_root.parent.parent.name} --work-item-id {item_root.name}`
- `python3 scripts/validate_coverage_matrix.py --input {rel(item_root / 'coverage' / 'coverage_matrix.json')} --schema schemas/coverage_matrix.schema.json`
"""
    write_text(generation_dir / "03-coverage-planner.md", content)


def build_testability_task(generation_dir: Path, item_root: Path) -> None:
    content = f"""# Testability Gate Run

- 角色：`Testability Analyst`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`

## 参考 Skill
- `skills/testability-gate/SKILL.md`

## 产出目标
- `{rel(item_root / 'acceptance' / 'testability_gate.md')}`
- `{rel(item_root / 'acceptance' / 'testability_gate.json')}`

## 强制要求
- 逐条规则区分 product acceptance、soft prompt、technical background、risk/API、待确认和非本期
- 不得把 soft prompt 升级为 hard block
- technical background 不得生成正式业务验证计划

## 校验命令
- `python3 skills/testability-gate/scripts/validate_testability_gate.py --input {rel(item_root / 'acceptance' / 'testability_gate.json')} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')}`
"""
    write_text(generation_dir / "03a-testability-gate.md", content)


def build_acceptance_task(
    generation_dir: Path,
    item_root: Path,
    work_item_level: str,
) -> None:
    content = f"""# Acceptance Examples Run

- 角色：`Acceptance Example Designer`
- 工作项级别：`{work_item_level}`
- 启用策略：`M/L 必须；S 可保持空投影但不得伪造 example`

## 输入
- `{rel(item_root / 'acceptance' / 'testability_gate.json')}`

## 参考 Skill
- `skills/acceptance-example/SKILL.md`

## 产出目标
- `{rel(item_root / 'acceptance' / 'acceptance_examples.md')}`
- `{rel(item_root / 'acceptance' / 'acceptance_examples.json')}`

## 校验命令
- `python3 skills/acceptance-example/scripts/validate_acceptance_examples.py --input {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')}`
"""
    write_text(generation_dir / "03b-acceptance-examples.md", content)


def build_test_design_task(
    generation_dir: Path,
    item_root: Path,
    work_item_level: str,
) -> None:
    content = f"""# Test Design Run

- 角色：`Test Design Planner`
- 工作项级别：`{work_item_level}`
- 启用策略：`L 必须；S/M 不得伪造 responsibility 或 matrix`

## 输入
- `{rel(item_root / 'acceptance' / 'testability_gate.json')}`
- `{rel(item_root / 'acceptance' / 'acceptance_examples.json')}`

## 参考 Skill
- `skills/test-design/SKILL.md`

## 产出目标
- `{rel(item_root / 'design' / 'verification_responsibility_map.md')}`
- `{rel(item_root / 'design' / 'verification_responsibility_map.json')}`
- `{rel(item_root / 'design' / 'test_design_matrix.md')}`
- `{rel(item_root / 'design' / 'test_design_matrix.json')}`

## 强制要求
- B端、C端、API、服务端强校验和风险责任分离
- code review 反馈只能进入 design 层，不得直接覆盖 testcase
"""
    write_text(generation_dir / "03c-test-design.md", content)


def build_case_plan_task(
    generation_dir: Path,
    item_root: Path,
    work_item_level: str,
) -> None:
    content = f"""# Case Plan Run

- 角色：`Case Planner`
- 工作项级别：`{work_item_level}`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'coverage' / 'coverage_matrix.json')}`
- `{rel(item_root / 'acceptance' / 'testability_gate.json')}`
- `{rel(item_root / 'acceptance' / 'acceptance_examples.json')}`
- `{rel(item_root / 'design' / 'verification_responsibility_map.json')}`
- `{rel(item_root / 'design' / 'test_design_matrix.json')}`

## 产出目标
- `{rel(item_root / 'testcases' / 'case_plan.md')}`
- `{rel(item_root / 'testcases' / 'case_plan.json')}`

## 强制要求
- 每个正式计划必须引用 gate；M/L 引用 example；L 引用 responsibility
- 每个 `should_generate_case=true` 计划必须提供 `source_coverage_ids` 或稳定的 `generated_testcase_ids`
- validation_path 决定主验收、API guard、risk note 和 out-of-scope 分池
- `should_generate_case=false` 的计划不得进入正式 testcase
"""
    write_text(generation_dir / "03d-case-plan.md", content)


def build_case_generator_task(generation_dir: Path, item_root: Path) -> None:
    references = [
        ROOT / "docs" / "testcase_signal_policy.md",
        ROOT / "scripts" / "generate_testcases_from_coverage.py",
        ROOT / "prompts" / "structured_to_cases_prompt.md",
        ROOT / "AGENTS.md",
        ROOT / "WORKFLOW_CONTRACT.md",
        ROOT / "skills" / "case-generation" / "templates" / "testpoints.template.md",
        ROOT / "skills" / "case-generation" / "templates" / "testpoints.template.json",
        ROOT / "skills" / "case-generation" / "scripts" / "generate_testpoints_view.py",
        ROOT / "skills" / "case-generation" / "scripts" / "validate_testpoints_view.py",
        ROOT / "skills" / "numbering-tagging" / "rules" / "numbering_rule.yaml",
        ROOT / "skills" / "numbering-tagging" / "rules" / "tag_rule.yaml",
        ROOT / "skills" / "numbering-tagging" / "rules" / "priority_rule.yaml",
    ]
    references.extend(
        existing_paths(
            ROOT / "tool_adapters" / "cursor" / "README.md",
        )
    )
    content = f"""# Case Generator Run

- 角色：`Case Generator`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'acceptance' / 'testability_gate.json')}`
- `{rel(item_root / 'acceptance' / 'acceptance_examples.json')}`
- `{rel(item_root / 'design' / 'verification_responsibility_map.json')}`
- `{rel(item_root / 'testcases' / 'case_plan.json')}`
- `{rel(item_root / 'coverage' / 'coverage_matrix.json')}`

## 参考规则
{build_file_list(references)}

## 产出目标
- `{rel(item_root / 'testcases' / 'testpoints.md')}`
- `{rel(item_root / 'testcases' / 'testpoints.json')}`
- `{rel(item_root / 'testcases' / 'testcases_main.md')}`
- `{rel(item_root / 'testcases' / 'dev_self_testcases.md')}`
- `{rel(item_root / 'testcases' / 'field_audit.json')}`
- `{rel(item_root / 'testcases' / 'grouped_audit.json')}`
- `{rel(item_root / 'testcases' / 'testcases.md')}`

## 强制要求
- 正式用例不再建议直接从 `structured_prd` 生成，必须先形成 `testability_gate` 与 `case_plan`
- `testability_gate` 必须过滤 technical_background / soft_prompt / risk_only / needs_confirmation / out_of_scope
- `case_plan` 必须具备来源、断言、验证端、优先级、用例类型和是否生成正式用例
- `testcases_main.md` 必须从 case_plan 派生，并通过 `generated_testcase_ids` 或备注 `来源 CasePlan：CP-xxx` 追溯
- `testpoints.md/json` 与 `testcases_main.md` 必须在 Case Generator 主流程中同步生成；测试点以 `case_plan.json` 为来源，并可从主用例补充页面/板块上下文
- `soft_prompt` 只能生成 prompt_display / ui_display，不得生成 hard_block
- `technical_background` 不能生成正式业务用例
- 主 testcase / audit 的信号判定必须以 `docs/testcase_signal_policy.md` 为准
- testcase 生成必须以 `coverage_matrix.json` 为主输入，以 `structured_prd.rules/fields` 为辅助输入
- `testcases_main.md` 是主用例真源，`testcases.md` 仅作为兼容镜像
- `dev_self_testcases.md` 必须从 `testcases_main.md` 中筛选 `开发必测` 标签派生，不得作为独立真源维护
- `field_audit.json` / `grouped_audit.json` 必须与主用例同步产出
- 必须覆盖单点用例与流程型用例
- 必须承接高优先级显式规则
- 对精确约束不得泛化改写
- 若 `fields[]` 与对象版 `rules[]` 已存在，必须优先从这两部分生成 testcase
- 优先消费 `explicit_rules[].fidelity_points`
- 若未显式给 `fidelity_points`，仍需保留高优先级显式规则中的时间、数量、来源、状态、排序、补齐、固定文案、样式差异、容器结果、默认状态、扩展性说明等原始值
- 对组合规则至少覆盖触发动作、目标容器、默认状态和容器内结果
- 对后台配置页，禁止默认生成 `字段矩阵完整性 / 条件联动` 这类摘要型用例
- 应优先生成“单规则单断言”用例，并额外补 1 条合法组合场景用例
- 必须显式覆盖：
  - 字段基础属性校验
  - 必填校验
  - 条件展示
  - 条件必填
  - 条件可编辑 / 只读
  - 边界值
  - 数据源过滤 / 展示格式 / 排序
  - 合法组合场景

## 校验命令
- `python3 skills/testability-gate/scripts/validate_testability_gate.py --input {rel(item_root / 'acceptance' / 'testability_gate.json')} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `python3 skills/acceptance-example/scripts/validate_acceptance_examples.py --input {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')}`
- `python3 skills/test-design/scripts/validate_responsibility_map.py --input {rel(item_root / 'design' / 'verification_responsibility_map.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')}`
- `python3 skills/case-generation/scripts/validate_case_plan.py --input {rel(item_root / 'testcases' / 'case_plan.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --acceptance-examples {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --require-examples`
- L 档 strict 额外执行：`python3 skills/case-generation/scripts/validate_case_plan.py --input {rel(item_root / 'testcases' / 'case_plan.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --acceptance-examples {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --responsibility-map {rel(item_root / 'design' / 'verification_responsibility_map.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --require-examples --require-responsibilities`
- `python3 scripts/generate_testcases_from_coverage.py --project-code {item_root.parent.parent.name} --work-item-id {item_root.name}`
- `python3 skills/case-generation/scripts/generate_testpoints_view.py --project-code {item_root.parent.parent.name} --work-item-id {item_root.name} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --json-output {rel(item_root / 'testcases' / 'testpoints.json')} --md-output {rel(item_root / 'testcases' / 'testpoints.md')}`
- `python3 skills/case-generation/scripts/validate_testpoints_view.py --input {rel(item_root / 'testcases' / 'testpoints.json')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --strict`
- `python3 scripts/build_dev_self_testcases.py --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --output {rel(item_root / 'testcases' / 'dev_self_testcases.md')}`
- `python3 skills/case-generation/scripts/testcase_lint.py --input {rel(item_root / 'testcases' / 'testcases_main.md')}`
"""
    write_text(generation_dir / "04-case-generator.md", content)


def build_reviewer_task(generation_dir: Path, item_root: Path, project_code: str, work_item_id: str) -> None:
    references = [
        ROOT / "docs" / "testcase_signal_policy.md",
        ROOT / "skills" / "review-gate" / "checklists" / "manual_review_checklist.md",
        ROOT / "prompts" / "review_fix_prompt.md",
    ]
    content = f"""# Case Reviewer Run

- 角色：`Case Reviewer`

## 输入
- `{rel(item_root / 'evidence' / 'evidence_inventory.json')}`
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'traceability' / 'coverage_first_traceability.json')}`
- `{rel(item_root / 'traceability' / 'traceability_adapter.json')}`
- `{rel(item_root / 'traceability' / 'traceability_matrix.json')}`
- `{rel(item_root / 'testcases' / 'testcases_main.md')}`
- `{rel(item_root / 'testcases' / 'testcases.md')}`
- `{rel(item_root / 'testcases' / 'field_audit.json')}`
- `{rel(item_root / 'testcases' / 'grouped_audit.json')}`

## 参考规则
{build_file_list(references)}

## 产出目标
- `{rel(item_root / 'reviews' / 'review_record.md')}`
- `{rel(item_root / 'reviews' / 'missing_rules.json')}`
- `{rel(item_root / 'reviews' / 'weak_cases.json')}`
- `{rel(item_root / 'reviews' / 'generalized_cases.json')}`
- `{rel(item_root / 'reviews' / 'quality_report.json')}`

## 强制要求
- generalized / weak / duplicate 等信号判断必须优先参考 `docs/testcase_signal_policy.md`
- 重点检查显式规则承接、精确约束保真、traceability 完整性
- `coverage_first_traceability.json` 是主 traceability 真源，`traceability_adapter.json` 是旧消费方兼容层，`traceability_matrix.json` 只做 legacy 对照
- 重点检查固定文案、样式差异、容器结果、默认状态、扩展性说明是否被保留
- 重点检查组合规则是否只保留终态、遗漏中间容器或默认状态
- reviewer 只做问题发现，不重写 testcase
- scorer 负责输出数字化质量报告
- 若发现问题，先产出 missing/weak/generalized/quality 报告，再补 review_record

## 校验命令
- `python3 scripts/review_and_score_testcases.py --project-code {project_code} --work-item-id {work_item_id}`
- `python3 scripts/validate_work_item.py --project-code {project_code} --work-item-id {work_item_id}`
"""
    write_text(generation_dir / "05-case-reviewer.md", content)


def build_formatter_task(generation_dir: Path, item_root: Path, project_code: str, work_item_id: str) -> None:
    content = f"""# Asset Formatter Run

- 角色：`Asset Formatter`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.md')}`
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'testcases' / 'testcases_main.md')}`
- `{rel(item_root / 'testcases' / 'testcases.md')}`
- `{rel(item_root / 'testcases' / 'field_audit.json')}`
- `{rel(item_root / 'testcases' / 'grouped_audit.json')}`
- `{rel(item_root / 'reviews' / 'review_record.md')}`

## 产出目标
- `{rel(item_root / 'feishu_ready.md')}`

## 校验命令
- `python3 scripts/export_feishu_ready.py --project-code {project_code} --work-item-id {work_item_id}`
    """
    write_text(generation_dir / "06-asset-formatter.md", content)


def build_frontend_cr_task(generation_dir: Path, item_root: Path) -> None:
    content = f"""# Frontend Code Review Run

- 角色：`Frontend Code Reviewer`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'traceability' / 'traceability_adapter.json')}`
- `{rel(item_root / 'testcases' / 'testcases_main.md')}`
- `{rel(item_root / 'testcases' / 'testcases.md')}`

## 产出目标
- `{rel(item_root / 'code_reviews' / 'frontend_code_review.md')}`
- `{rel(item_root / 'code_reviews' / 'frontend_confirmation.json')}`

## 强制要求
- 本阶段只做代码与用例相互映证，不修改业务代码
- 本阶段不修改历史产出物，只输出 CR 结论与人工确认结果
- 优先识别：点击能力、显隐状态、固定文案、样式差异、容器结果、计时器、前端排序/过滤/补齐行为
- 对每个映证点补充：`implementation_binding / recommended_cr_stage / manual_confirmation_required / cr_focus_points`
- 前端 CR 完成后，必须人工确认 `frontend_confirmation.json`
"""
    write_text(generation_dir / "07-frontend-code-review.md", content)


def build_backend_cr_task(generation_dir: Path, item_root: Path) -> None:
    content = f"""# Backend Code Review Run

- 角色：`Backend Code Reviewer`

## 输入
- `{rel(item_root / 'structured_prd' / 'structured_prd.json')}`
- `{rel(item_root / 'traceability' / 'traceability_adapter.json')}`
- `{rel(item_root / 'testcases' / 'testcases_main.md')}`
- `{rel(item_root / 'testcases' / 'testcases.md')}`

## 产出目标
- `{rel(item_root / 'code_reviews' / 'backend_code_review.md')}`
- `{rel(item_root / 'code_reviews' / 'backend_confirmation.json')}`

## 强制要求
- 本阶段只做接口契约、数据来源、状态过滤、排序、分页、默认值、补齐逻辑映证，不修改业务代码
- 本阶段不修改历史产出物，只输出 CR 结论与人工确认结果
- 优先识别：后端数据来源、枚举值、过滤条件、排序主次规则、分页字段、默认返回、补齐逻辑、共享契约
- 对每个映证点补充：`implementation_binding / recommended_cr_stage / manual_confirmation_required / cr_focus_points`
- 后端 CR 完成后，必须人工确认 `backend_confirmation.json`
"""
    write_text(generation_dir / "08-backend-code-review.md", content)


def build_preflight_task(generation_dir: Path, item_root: Path) -> None:
    image_evidence_path = item_root / "image_evidence" / "image_evidence_inventory.json"
    outputs = [
        item_root / "inputs" / "requirement_summary.md",
        item_root / "inputs" / "source_manifest.json",
    ]
    if image_evidence_path.exists():
        outputs.append(image_evidence_path)
    outputs.extend(
        [
            item_root / "analysis" / "analysis_report.md",
            item_root / "analysis" / "reasoning_pack.json",
            item_root / "coverage" / "coverage_matrix.json",
            item_root / "evidence" / "evidence_inventory.json",
            item_root / "structured_prd" / "structured_prd.json",
            item_root / "acceptance" / "testability_gate.md",
            item_root / "acceptance" / "testability_gate.json",
            item_root / "acceptance" / "acceptance_examples.md",
            item_root / "acceptance" / "acceptance_examples.json",
            item_root / "design" / "verification_responsibility_map.md",
            item_root / "design" / "verification_responsibility_map.json",
            item_root / "design" / "test_design_matrix.md",
            item_root / "design" / "test_design_matrix.json",
            item_root / "traceability" / "coverage_first_traceability.json",
            item_root / "traceability" / "traceability_adapter.json",
            item_root / "traceability" / "traceability_matrix.json",
            item_root / "testcases" / "case_plan.md",
            item_root / "testcases" / "case_plan.json",
            item_root / "testcases" / "testpoints.md",
            item_root / "testcases" / "testpoints.json",
            item_root / "testcases" / "testcases_main.md",
            item_root / "testcases" / "dev_self_testcases.md",
            item_root / "testcases" / "testcases.md",
            item_root / "testcases" / "field_audit.json",
            item_root / "testcases" / "grouped_audit.json",
            item_root / "reviews" / "review_record.md",
            item_root / "reviews" / "missing_rules.json",
            item_root / "reviews" / "missing_fidelity_points.json",
            item_root / "reviews" / "fidelity_hit_locations.json",
            item_root / "reviews" / "duplicate_case_report.json",
            item_root / "reviews" / "weak_cases.json",
            item_root / "reviews" / "generalized_cases.json",
            item_root / "reviews" / "quality_report.json",
            item_root / "feishu_ready.md",
        ]
    )
    content = f"""# Regeneration Preflight

## 本次重跑默认清理目标
{build_file_list(outputs)}

## 重跑前检查
- 输入资料是否已放入 `inputs/`
- 若存在原始截图，是否已放入 `inputs/images/`
- 若输入主要是截图，是否已产出 `image_evidence_inventory.json`
- 是否存在新增补充文档未进入任务包
- 是否已确认本次要以最新 rules / prompts / schema 为准
- 是否已检查固定文案、样式差异、容器结果、默认状态、扩展性说明
- 是否已检查组合规则的触发动作、目标容器、默认状态和容器内结果
- 是否已识别哪些检查点更适合在前端 CR 或后端 CR 阶段执行
- 是否已确认代码评审产物不允许覆盖业务代码或历史产物
- 若需清理旧产物，先备份或归档后再执行重生成

## 建议顺序
1. 清理旧产物
2. 执行 Requirement Summarizer
3. 执行 Reasoning Analyst
4. 执行 PRD Structurer
5. 执行 Coverage Planner
6. 执行 Testability Gate
7. 按 S/M/L 执行 Acceptance Examples 与 Test Design
8. 执行 Case Planner
9. 执行 Case Generator（同步产出 testpoints + testcases）
10. 执行 Case Reviewer
11. 执行 Frontend Code Reviewer
12. 执行 Backend Code Reviewer
13. 执行 Asset Formatter
14. 执行统一校验
"""
    write_text(generation_dir / "00-preflight.md", content)


def build_run_manifest(
    generation_dir: Path,
    item_root: Path,
    manifest: dict,
    input_files: list[Path],
    project_code: str,
    work_item_id: str,
    work_item_level: str,
) -> None:
    image_evidence_path = item_root / "image_evidence" / "image_evidence_inventory.json"
    design_decision_paths = [
        item_root / "acceptance" / "testability_gate.md",
        item_root / "acceptance" / "testability_gate.json",
        item_root / "acceptance" / "acceptance_examples.md",
        item_root / "acceptance" / "acceptance_examples.json",
        item_root / "design" / "verification_responsibility_map.md",
        item_root / "design" / "verification_responsibility_map.json",
        item_root / "design" / "test_design_matrix.md",
        item_root / "design" / "test_design_matrix.json",
        item_root / "testcases" / "case_plan.md",
        item_root / "testcases" / "case_plan.json",
    ]
    existing_design_decision_targets = [rel(path) for path in design_decision_paths if path.exists()]
    design_decision_validate_commands = []
    if (item_root / "acceptance" / "testability_gate.json").exists():
        design_decision_validate_commands.append(
            f"python3 skills/testability-gate/scripts/validate_testability_gate.py --input {rel(item_root / 'acceptance' / 'testability_gate.json')} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')}"
        )
    if (item_root / "testcases" / "case_plan.json").exists():
        if (item_root / "acceptance" / "acceptance_examples.json").exists():
            design_decision_validate_commands.append(
                f"python3 skills/acceptance-example/scripts/validate_acceptance_examples.py --input {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')}"
            )
        if (item_root / "design" / "verification_responsibility_map.json").exists():
            design_decision_validate_commands.append(
                f"python3 skills/test-design/scripts/validate_responsibility_map.py --input {rel(item_root / 'design' / 'verification_responsibility_map.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')}"
            )
        if (
            work_item_level == "L"
            and (item_root / "design" / "test_design_matrix.json").exists()
        ):
            design_decision_validate_commands.append(
                f"python3 skills/test-design/scripts/validate_test_design_matrix.py --input {rel(item_root / 'design' / 'test_design_matrix.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --acceptance-examples {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --responsibility-map {rel(item_root / 'design' / 'verification_responsibility_map.json')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')}"
            )
        design_decision_validate_commands.append(
            f"python3 skills/case-generation/scripts/validate_case_plan.py --input {rel(item_root / 'testcases' / 'case_plan.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --acceptance-examples {rel(item_root / 'acceptance' / 'acceptance_examples.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')}"
        )
    payload = {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "work_item_level": work_item_level,
        "title": manifest.get("title", "待确认"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": [rel(path) for path in input_files],
        "roles": [
            "Requirement Summarizer",
            "Reasoning Analyst",
            "PRD Structurer",
            "Coverage Planner",
            "Testability Analyst",
            "Acceptance Example Designer",
            "Test Design Planner",
            "Case Planner",
            "Case Generator",
            "Case Reviewer",
            "Frontend Code Reviewer",
            "Backend Code Reviewer",
            "Asset Formatter",
        ],
        "task_files": [
            rel(generation_dir / "00-preflight.md"),
            rel(generation_dir / "00-requirement-intake.md"),
            rel(generation_dir / "01-reasoning-analyst.md"),
            rel(generation_dir / "02-prd-structurer.md"),
            rel(generation_dir / "03-coverage-planner.md"),
            rel(generation_dir / "03a-testability-gate.md"),
            rel(generation_dir / "03b-acceptance-examples.md"),
            rel(generation_dir / "03c-test-design.md"),
            rel(generation_dir / "03d-case-plan.md"),
            rel(generation_dir / "04-case-generator.md"),
            rel(generation_dir / "05-case-reviewer.md"),
            rel(generation_dir / "07-frontend-code-review.md"),
            rel(generation_dir / "08-backend-code-review.md"),
            rel(generation_dir / "06-asset-formatter.md"),
        ],
        "cleanup_targets": [
            rel(item_root / "inputs" / "requirement_summary.md"),
            rel(item_root / "inputs" / "source_manifest.json"),
            *([rel(image_evidence_path)] if image_evidence_path.exists() else []),
            rel(item_root / "analysis" / "analysis_report.md"),
            rel(item_root / "analysis" / "reasoning_pack.json"),
            rel(item_root / "coverage" / "coverage_matrix.json"),
            rel(item_root / "evidence" / "evidence_inventory.json"),
            rel(item_root / "structured_prd" / "structured_prd.md"),
            rel(item_root / "structured_prd" / "structured_prd.json"),
            *existing_design_decision_targets,
            rel(item_root / "traceability" / "coverage_first_traceability.json"),
            rel(item_root / "traceability" / "traceability_adapter.json"),
            rel(item_root / "traceability" / "traceability_matrix.json"),
            rel(item_root / "testcases" / "testcases_main.md"),
            rel(item_root / "testcases" / "dev_self_testcases.md"),
            rel(item_root / "testcases" / "testpoints.md"),
            rel(item_root / "testcases" / "testpoints.json"),
            rel(item_root / "testcases" / "testcases.md"),
            rel(item_root / "testcases" / "field_audit.json"),
            rel(item_root / "testcases" / "grouped_audit.json"),
            rel(item_root / "reviews" / "review_record.md"),
            rel(item_root / "reviews" / "missing_rules.json"),
            rel(item_root / "reviews" / "missing_fidelity_points.json"),
            rel(item_root / "reviews" / "fidelity_hit_locations.json"),
            rel(item_root / "reviews" / "duplicate_case_report.json"),
            rel(item_root / "reviews" / "weak_cases.json"),
            rel(item_root / "reviews" / "generalized_cases.json"),
            rel(item_root / "reviews" / "quality_report.json"),
            rel(item_root / "feishu_ready.md"),
        ],
        "validate_commands": [
            f"python3 scripts/validate_requirement_sources.py --input {rel(item_root / 'inputs' / 'source_manifest.json')} --strict",
            f"python3 scripts/generate_reasoning_pack.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/validate_reasoning_pack.py --input {rel(item_root / 'analysis' / 'reasoning_pack.json')} --schema schemas/reasoning_pack.schema.json",
            f"python3 scripts/project_reasoning_to_structured_prd.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/generate_coverage_matrix.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/validate_coverage_matrix.py --input {rel(item_root / 'coverage' / 'coverage_matrix.json')} --schema schemas/coverage_matrix.schema.json",
            *(
                [
                    f"python3 scripts/compile_structured_prd_json.py --input {rel(item_root / 'structured_prd' / 'structured_prd.md')} --output {rel(item_root / 'structured_prd' / 'structured_prd.json')}",
                    f"python3 skills/prd-image-evidence-extractor/scripts/validate_image_evidence.py --input {rel(image_evidence_path)}",
                    f"python3 scripts/validate_image_evidence_mapping.py --image-evidence {rel(image_evidence_path)} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')}",
                    f"python3 scripts/sync_modal_attributes_from_image_evidence.py --image-evidence {rel(image_evidence_path)} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')} --write",
                    f"python3 scripts/expand_backend_field_traceability.py --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')} --traceability {rel(item_root / 'traceability' / 'traceability_matrix.json')} --write",
                    *(
                        [
                            f"python3 scripts/validate_backend_config_chain.py --image-evidence {rel(image_evidence_path)} --evidence {rel(item_root / 'evidence' / 'evidence_inventory.json')} --structured-prd {rel(item_root / 'structured_prd' / 'structured_prd.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')}"
                        ]
                        if should_run_backend_config_chain(image_evidence_path)
                        else []
                    ),
                ]
                if image_evidence_path.exists()
                else []
            ),
            f"python3 scripts/compile_structured_prd_json.py --input {rel(item_root / 'structured_prd' / 'structured_prd.md')} --output {rel(item_root / 'structured_prd' / 'structured_prd.json')}",
            f"python3 skills/prd-structuring/scripts/validate_structured_prd.py --input {rel(item_root / 'structured_prd' / 'structured_prd.json')} --schema schemas/structured_prd.schema.json",
            *design_decision_validate_commands,
            f"python3 skills/case-generation/scripts/generate_testpoints_view.py --project-code {project_code} --work-item-id {work_item_id} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --json-output {rel(item_root / 'testcases' / 'testpoints.json')} --md-output {rel(item_root / 'testcases' / 'testpoints.md')}",
            f"python3 skills/case-generation/scripts/validate_testpoints_view.py --input {rel(item_root / 'testcases' / 'testpoints.json')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')} --testability-gate {rel(item_root / 'acceptance' / 'testability_gate.json')} --strict",
            f"python3 skills/case-generation/scripts/testcase_lint.py --input {rel(item_root / 'testcases' / 'testcases_main.md')}",
            f"python3 scripts/build_dev_self_testcases.py --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --output {rel(item_root / 'testcases' / 'dev_self_testcases.md')}",
            f"python3 scripts/build_testcase_bundle.py --project-code {project_code} --work-item-id {work_item_id} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --output {rel(item_root / 'testcases' / 'testcase_bundle.json')}",
            f"python3 scripts/validate_testcase_bundle.py --input {rel(item_root / 'testcases' / 'testcase_bundle.json')} --testcases {rel(item_root / 'testcases' / 'testcases_main.md')} --case-plan {rel(item_root / 'testcases' / 'case_plan.json')} --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/build_coverage_first_traceability.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/build_traceability_adapter.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/slim_legacy_traceability.py --project-code {project_code} --work-item-id {work_item_id} --write",
            f"python3 scripts/review_and_score_testcases.py --project-code {project_code} --work-item-id {work_item_id}",
            f"python3 scripts/validate_code_review_assets.py --frontend-review {rel(item_root / 'code_reviews' / 'frontend_code_review.md')} --frontend-confirmation {rel(item_root / 'code_reviews' / 'frontend_confirmation.json')} --backend-review {rel(item_root / 'code_reviews' / 'backend_code_review.md')} --backend-confirmation {rel(item_root / 'code_reviews' / 'backend_confirmation.json')}",
            f"python3 scripts/validate_work_item.py --project-code {project_code} --work-item-id {work_item_id} --work-item-level {work_item_level} --strict",
            f"python3 scripts/export_feishu_ready.py --project-code {project_code} --work-item-id {work_item_id}",
        ],
    }
    write_text(
        generation_dir / "run_manifest.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为工作项生成可重跑的任务包入口")
    parser.add_argument("--project-code", required=True, help="项目编码")
    parser.add_argument("--work-item-id", required=True, help="工作项 ID")
    parser.add_argument(
        "--work-item-level",
        choices=sorted(VALID_WORK_ITEM_LEVELS),
        default=None,
        help="显式覆盖 manifest 中的工作项级别；未指定时读取 manifest，缺失回退 M",
    )
    parser.add_argument(
        "--output-dir-name",
        default=".generation/latest",
        help="生成任务包的相对目录，默认 .generation/latest",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_code = normalize_code(args.project_code)
    work_item_id = normalize_code(args.work_item_id)
    item_root = work_item_root(project_code, work_item_id)

    if not item_root.exists():
        raise SystemExit(f"工作项不存在: {item_root}")

    manifest_path = item_root / "manifest.json"
    inputs_dir = item_root / "inputs"
    if not manifest_path.exists():
        raise SystemExit(f"manifest 不存在: {manifest_path}")
    if not inputs_dir.exists():
        raise SystemExit(f"inputs 目录不存在: {inputs_dir}")

    manifest = read_json(manifest_path)
    work_item_level, work_item_level_source = resolve_work_item_level(
        manifest,
        args.work_item_level,
    )
    input_files = list_input_files(inputs_dir)
    generation_dir = item_root / Path(args.output_dir_name)
    ensure_dir(generation_dir)
    removed = remove_stale_generation_files(generation_dir)

    build_requirement_intake_task(generation_dir, item_root, manifest, input_files)
    build_reasoning_task(generation_dir, item_root, manifest, input_files)
    build_structurer_task(generation_dir, item_root, manifest, input_files)
    build_coverage_planner_task(generation_dir, item_root)
    build_testability_task(generation_dir, item_root)
    build_acceptance_task(generation_dir, item_root, work_item_level)
    build_test_design_task(generation_dir, item_root, work_item_level)
    build_case_plan_task(generation_dir, item_root, work_item_level)
    build_preflight_task(generation_dir, item_root)
    build_case_generator_task(generation_dir, item_root)
    build_reviewer_task(generation_dir, item_root, project_code, work_item_id)
    build_frontend_cr_task(generation_dir, item_root)
    build_backend_cr_task(generation_dir, item_root)
    build_formatter_task(generation_dir, item_root, project_code, work_item_id)
    build_run_manifest(
        generation_dir,
        item_root,
        manifest,
        input_files,
        project_code,
        work_item_id,
        work_item_level,
    )

    print(f"已生成重跑任务包: {generation_dir}")
    print(f"工作项级别: {work_item_level} (source={work_item_level_source})")
    if removed:
        print("已清理旧流程残留任务文件:")
        for path in removed:
            print(f"- {path}")
    print("包含文件:")
    for name in [*CURRENT_TASK_FILES, "run_manifest.json"]:
        print(f"- {generation_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
