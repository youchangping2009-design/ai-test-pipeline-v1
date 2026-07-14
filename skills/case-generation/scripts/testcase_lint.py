#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
testcase_lint.py

用途：
1. 校验 Markdown 测试用例表结构是否合法
2. 检查单点用例与流程型用例的基础质量
3. 按最新规则校验标签、测试类型、编号、Flow 流程型用例质量

推荐用法：
python skills/case-generation/scripts/testcase_lint.py \
  --input assets/projects/WX-YYPT/testcases/demo.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document

VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}

# 流程类测试类型
FLOW_TEST_TYPES = {"流程验证", "状态流转", "数据校验"}

# 最新标签封闭集合
ALLOWED_TAGS = {
    "核心链路",
    "黄金用例",
    "AI-API用例",
    "AI-UI用例",
    "测试必测",
    "开发必测",
    "评审用例",
}

# 自动化执行载体标签
AUTOMATION_CARRIER_TAGS = {
    "AI-API用例",
    "AI-UI用例",
}

# 人工执行责任标签
RESPONSIBILITY_TAGS = {
    "测试必测",
    "开发必测",
}

# 明确禁止出现在标签中的内容（旧规则 / 错位信息）
FORBIDDEN_TAGS = {
    "流程型用例",
    "单点用例",
    "跨模块",
    "发布必测",
    "数据正确性",
    "展示相关",
    "配置相关",
    "功能",
    "边界",
    "异常",
    "权限",
    "流程验证",
    "状态流转",
    "数据校验",
    "回归",
    "B端",
    "C端",
    "后台",
    "H5",
    "小程序",
    "接口",
    "服务端",
    "首页",
    "游戏官网",
    "页游顶栏",
    "登录弹窗",
    "注册弹窗",
    "选服弹窗",
    "顶部导航",
    "导航栏",
    "banner",
    "用户信息区",
    "开服列表",
    "游戏列表",
    "游戏公告",
    "区服选择",
    "底栏",
}

GENERIC_TITLE_PATTERNS = [
    r"验证功能正常",
    r"验证流程正常",
    r"验证是否成功",
    r"验证主流程正常",
    r"验证配置是否成功",
]

GENERIC_EXPECTED_PATTERNS = [
    r"正常",
    r"成功",
    r"符合预期",
    r"页面正常",
    r"结果正确",
]

GENERIC_STEP_PATTERNS = [
    r"执行操作",
    r"进行测试",
    r"验证功能",
    r"点击按钮",
    r"输入内容",
]

MACHINE_FIELD_PATTERN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")

# 编号格式：PROJECT-PAGE-PAGEMODULE-TERMINAL-TYPE-SEQ
# 例如：WX-YYPT-HOME-NAV-WEB-FN-001
CASE_ID_PATTERN = re.compile(
    r"^[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-(FN|BD|AB|PM|FL|ST|DV)-\d{3,}$"
)

TEST_TYPE_TO_CODE = {
    "功能": "FN",
    "边界": "BD",
    "异常": "AB",
    "权限": "PM",
    "流程验证": "FL",
    "状态流转": "ST",
    "数据校验": "DV",
}


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def contains_pattern(text: str, patterns: List[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def split_tags(tag_text: str) -> List[str]:
    """
    支持中英文逗号、顿号、分号。
    """
    if not tag_text.strip():
        return []
    parts = re.split(r"[，,、；;]", tag_text)
    return [p.strip() for p in parts if p.strip()]


def extract_type_code(case_id: str) -> str | None:
    """
    从编号中提取 type_code。
    """
    parts = case_id.split("-")
    if len(parts) < 2:
        return None
    candidate = parts[-2]
    if candidate in {"FN", "BD", "AB", "PM", "FL", "ST", "DV"}:
        return candidate
    return None


def is_flow_case(row: Dict[str, str]) -> bool:
    """
    Flow 用例识别逻辑（新版）：
    1. 测试类型为流程验证
    2. 备注中带来源 Flow
    3. 编号 type_code 为 FL

    说明：
    - `状态流转` / `数据校验` 可用于单点 API 用例
    - 不应仅因测试类型为 ST / DV 就按 Flow 用例规则校验
    """
    test_type = row["测试类型"].strip()
    remark = row["备注"]
    case_id = row["用例编号"].strip()

    if test_type == "流程验证":
        return True
    if "来源 Flow：" in remark or "来源Flow：" in remark:
        return True

    type_code = extract_type_code(case_id)
    if type_code == "FL":
        return True

    return False


def lint_basic_required_fields(rows: List[Dict[str, str]]) -> List[str]:
    errors = []
    required_fields = [
        "用例编号",
        "所属模块",
        "所属功能点",
        "用例标题",
        "前置条件",
        "测试步骤",
        "预期结果",
        "优先级",
        "标签",
        "测试类型",
    ]

    for idx, row in enumerate(rows, start=1):
        for field in required_fields:
            if not row[field].strip():
                errors.append(f"[基础校验失败] 第 {idx} 条用例字段为空: {field}")

    return errors


def lint_case_id_uniqueness(rows: List[Dict[str, str]]) -> List[str]:
    errors = []
    seen = set()
    for idx, row in enumerate(rows, start=1):
        case_id = row["用例编号"].strip()
        if case_id in seen:
            errors.append(f"[编号校验失败] 第 {idx} 条用例编号重复: {case_id}")
        seen.add(case_id)
    return errors


def lint_case_id_format(rows: List[Dict[str, str]]) -> List[str]:
    errors = []

    for idx, row in enumerate(rows, start=1):
        case_id = row["用例编号"].strip()
        test_type = row["测试类型"].strip()

        if not CASE_ID_PATTERN.match(case_id):
            errors.append(
                f"[编号校验失败] 第 {idx} 条用例编号格式不符合规则: {case_id}"
            )
            continue

        # 编号 type_code 与 测试类型 字段一致性校验
        expected_code = TEST_TYPE_TO_CODE.get(test_type)
        actual_code = extract_type_code(case_id)

        if expected_code is not None and actual_code != expected_code:
            errors.append(
                f"[编号校验失败] 第 {idx} 条用例编号 type_code 与测试类型不一致: "
                f"case_id={case_id}, 测试类型={test_type}, 期望={expected_code}, 实际={actual_code}"
            )

    return errors


def lint_priority(rows: List[Dict[str, str]]) -> List[str]:
    errors = []
    for idx, row in enumerate(rows, start=1):
        priority = row["优先级"].strip()
        if priority not in VALID_PRIORITIES:
            errors.append(f"[优先级校验失败] 第 {idx} 条用例优先级非法: {priority}")
    return errors


def lint_generic_quality(rows: List[Dict[str, str]]) -> List[str]:
    errors = []

    for idx, row in enumerate(rows, start=1):
        title = row["用例标题"]
        steps = row["测试步骤"]
        expected = row["预期结果"]

        if contains_pattern(title, GENERIC_TITLE_PATTERNS):
            errors.append(f"[质量校验失败] 第 {idx} 条用例标题过于泛化: {title}")

        if contains_pattern(expected, GENERIC_EXPECTED_PATTERNS):
            errors.append(f"[质量校验失败] 第 {idx} 条用例预期结果过于模糊: {expected}")

        if contains_pattern(steps, GENERIC_STEP_PATTERNS):
            errors.append(f"[质量校验失败] 第 {idx} 条用例测试步骤过于泛化: {steps}")

    return errors


def lint_human_readable_copy(rows: List[Dict[str, str]]) -> List[str]:
    errors: List[str] = []
    checked_fields = ["用例标题", "前置条件", "测试步骤", "预期结果"]
    for idx, row in enumerate(rows, start=1):
        for field in checked_fields:
            text = row.get(field, "")
            hits = sorted(set(MACHINE_FIELD_PATTERN.findall(text)))
            if not hits:
                continue
            errors.append(
                f"[可读性校验失败] 第 {idx} 条用例 {field} 不应直接暴露机器字段名: {hits}"
            )
    return errors


def lint_tags(rows: List[Dict[str, str]]) -> List[str]:
    errors = []

    for idx, row in enumerate(rows, start=1):
        tag_text = row["标签"]
        tags = split_tags(tag_text)
        tag_set: Set[str] = set(tags)

        # 1. 标签不能为空（因为至少要有一个载体或责任标签）
        if not tags:
            errors.append(f"[标签校验失败] 第 {idx} 条用例标签为空")
            continue

        # 2. 禁止使用封闭集合之外的标签
        unknown_tags = [t for t in tags if t not in ALLOWED_TAGS]
        if unknown_tags:
            errors.append(
                f"[标签校验失败] 第 {idx} 条用例存在未登记标签: {unknown_tags}"
            )

        # 3. 显式拦截旧标签/错位标签
        forbidden_hit = [t for t in tags if t in FORBIDDEN_TAGS]
        if forbidden_hit:
            errors.append(
                f"[标签校验失败] 第 {idx} 条用例使用了禁止标签: {forbidden_hit}"
            )

        # 4. 每条用例至少命中 1 个自动化执行载体或人工执行责任标签
        if not (tag_set & (AUTOMATION_CARRIER_TAGS | RESPONSIBILITY_TAGS)):
            errors.append(
                f"[标签校验失败] 第 {idx} 条用例至少应包含 1 个自动化执行载体或人工执行责任标签："
                f"{sorted(AUTOMATION_CARRIER_TAGS | RESPONSIBILITY_TAGS)}"
            )

        # 5. 核心流程或关键变更必须由开发和测试共同兜底
        priority = row.get("优先级", "").strip()
        if "核心链路" in tag_set or "黄金用例" in tag_set or priority == "P0":
            missing = [tag for tag in ["开发必测", "测试必测"] if tag not in tag_set]
            if missing:
                errors.append(
                    f"[标签校验失败] 第 {idx} 条核心流程/关键变更用例缺少责任标签: {missing}"
                )

    return errors


def lint_flow_cases(rows: List[Dict[str, str]]) -> List[str]:
    errors = []

    flow_case_count = 0
    p0_flow_count = 0

    for idx, row in enumerate(rows, start=1):
        if not is_flow_case(row):
            continue

        flow_case_count += 1

        tags = split_tags(row["标签"])
        tag_set = set(tags)
        test_type = row["测试类型"].strip()
        title = row["用例标题"]
        remark = row["备注"]
        priority = row["优先级"].strip()
        module_name = row["所属模块"].strip()
        feature_name = row["所属功能点"].strip()
        steps = row["测试步骤"]
        expected = row["预期结果"]
        case_id = row["用例编号"].strip()

        # 1. Flow 用例测试类型必须合理
        if test_type not in FLOW_TEST_TYPES:
            errors.append(
                f"[Flow校验失败] 第 {idx} 条流程类用例测试类型不合理: {test_type}，"
                f"建议使用 {sorted(FLOW_TEST_TYPES)}"
            )

        # 2. 备注中必须带来源 Flow
        if "来源 Flow：" not in remark and "来源Flow：" not in remark:
            errors.append(f"[Flow校验失败] 第 {idx} 条流程类用例备注缺少来源 Flow 标识")

        # 3. 标题不能过泛
        if contains_pattern(title, GENERIC_TITLE_PATTERNS):
            errors.append(f"[Flow校验失败] 第 {idx} 条流程类用例标题过于泛化: {title}")

        # 4. 所属模块 / 功能点不能空泛
        if module_name in {"多个模块", "主流程", "流程"}:
            errors.append(f"[Flow校验失败] 第 {idx} 条流程类用例所属模块过于泛化: {module_name}")

        if feature_name in {"主流程", "流程", "功能流程"}:
            errors.append(f"[Flow校验失败] 第 {idx} 条流程类用例所属功能点过于泛化: {feature_name}")

        # 5. 步骤需具备链路感
        if "<br>" not in steps and "1." not in steps:
            errors.append(f"[Flow校验失败] 第 {idx} 条流程类用例步骤疑似不完整")

        # 6. 预期结果应体现终态/关键结果
        terminal_keywords = ["状态", "生效", "可见", "完成", "成功发布", "流转", "回传", "展示", "进入游戏"]
        if not any(keyword in expected for keyword in terminal_keywords):
            errors.append(
                f"[Flow校验失败] 第 {idx} 条流程类用例预期结果未明显体现流程终态/关键结果"
            )

        # 7. 若带核心链路/黄金用例，优先级建议 P0
        if "黄金用例" in tag_set or "核心链路" in tag_set:
            if priority != "P0":
                errors.append(
                    f"[Flow校验失败] 第 {idx} 条带黄金用例/核心链路标签的流程类用例优先级建议为 P0，当前为 {priority}"
                )

        # 8. Flow 用例的编号 type_code 应为 FL/ST/DV
        type_code = extract_type_code(case_id)
        if type_code not in {"FL", "ST", "DV"}:
            errors.append(
                f"[Flow校验失败] 第 {idx} 条流程类用例编号 type_code 应为 FL/ST/DV，当前为 {type_code}"
            )

        if priority == "P0":
            p0_flow_count += 1

    # 9. 至少存在一条流程类用例
    if flow_case_count == 0:
        errors.append("[Flow校验失败] 未检测到任何流程类用例")

    # 10. 至少存在一条 P0 流程类用例
    if flow_case_count > 0 and p0_flow_count == 0:
        errors.append("[Flow校验失败] 检测到流程类用例，但未发现任何 P0 流程类用例")

    return errors


def lint_backend_config_crud_chains(rows: List[Dict[str, str]]) -> List[str]:
    """后台配置页需要真实新增/编辑/删除链路，不能只停留在字段校验。"""
    errors: List[str] = []
    action_keywords = {
        "真实新增": ("真实新增", "点击`添加`", "点击添加", "列表新增", "新增1条"),
        "真实编辑": ("真实编辑", "点击目标记录`编辑`", "点击编辑", "原记录被更新", "不新增重复记录"),
        "真实删除": ("真实删除", "点击目标记录`删除`", "点击删除", "列表中不再展示", "从列表移除"),
    }

    module_rows_by_name: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        module_name = row.get("所属模块", "").strip()
        if module_name:
            module_rows_by_name.setdefault(module_name, []).append(row)

    modules_present: Set[str] = set()
    for module_name, module_rows in module_rows_by_name.items():
        corpus = " ".join(
            " ".join(
                [
                    row.get("所属功能点", ""),
                    row.get("用例标题", ""),
                    row.get("前置条件", ""),
                    row.get("测试步骤", ""),
                    row.get("预期结果", ""),
                ]
            )
            for row in module_rows
        )
        has_config_entity = "配置" in module_name
        has_dialog_or_list_save = any(keyword in corpus for keyword in ["添加弹窗", "编辑弹窗", "列表", "保存"])
        has_distribution_controls = any(
            keyword in corpus
            for keyword in ["展示tab", "跳转类型", "展示类型", "触达用户类型", "展示规则", "链接", "选择活动"]
        )
        has_status = "状态" in corpus
        if has_config_entity and has_dialog_or_list_save and has_distribution_controls and has_status:
            modules_present.add(module_name)

    if not modules_present:
        return errors

    for module_name in sorted(modules_present):
        module_rows = [row for row in rows if row.get("所属模块", "").strip() == module_name]
        for action_name, keywords in action_keywords.items():
            matched = False
            for row in module_rows:
                row_text = " ".join(
                    [
                        row.get("用例标题", ""),
                        row.get("测试步骤", ""),
                        row.get("预期结果", ""),
                        row.get("备注", ""),
                    ]
                )
                if any(keyword in row_text for keyword in keywords):
                    matched = True
                    break
            if not matched:
                errors.append(
                    f"[后台配置CRUD校验失败] {module_name} 缺少{action_name}链路用例，"
                    "需要覆盖点击入口、保存/确认、列表结果变化"
                )

    return errors


def lint_grouping_structure(parsed: Dict[str, object], rows: List[Dict[str, str]]) -> List[str]:
    errors: List[str] = []
    tables = parsed.get("tables", [])
    page_names = parsed.get("page_names", [])
    section_names = parsed.get("section_names", [])

    if not rows:
        return errors

    if len(tables) > 1 and not page_names:
        errors.append("[结构校验失败] 检测到多张用例表，但未使用“页面：”标题进行页面分组")

    if section_names and not page_names:
        errors.append("[结构校验失败] 已使用“板块：”标题，但缺少对应的“页面：”标题")

    for idx, table in enumerate(tables, start=1):
        table_rows = table.get("rows", [])
        if not table_rows:
            continue
        if page_names and not table.get("page_name"):
            errors.append(f"[结构校验失败] 第 {idx} 个用例表缺少页面分组标题")
        if len(tables) > 1 and not table.get("section_name"):
            errors.append(f"[结构校验失败] 第 {idx} 个用例表缺少板块分组标题")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Markdown 测试用例表")
    parser.add_argument(
        "--input",
        required=True,
        help="待校验的 Markdown 测试用例文件路径",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()

    try:
        content = read_text(input_path)
    except Exception as exc:
        print(f"读取输入文件失败: {exc}", file=sys.stderr)
        return 1

    try:
        parsed = parse_testcase_document(content, strict=True)
        rows = parsed["rows"]
    except Exception as exc:
        print(f"❌ 表格解析失败: {exc}", file=sys.stderr)
        return 1

    # 初始化模板：只有表头和分隔行，没有真实数据
    if not rows:
        print("✅ 测试用例校验通过")
        print(f"输入文件: {input_path}")
        print("当前文件为初始化模板，仅包含表头，尚无真实用例数据")
        return 0

    all_errors: List[str] = []
    all_errors.extend(lint_basic_required_fields(rows))
    all_errors.extend(lint_case_id_uniqueness(rows))
    all_errors.extend(lint_case_id_format(rows))
    all_errors.extend(lint_priority(rows))
    all_errors.extend(lint_tags(rows))
    all_errors.extend(lint_generic_quality(rows))
    all_errors.extend(lint_human_readable_copy(rows))
    all_errors.extend(lint_flow_cases(rows))
    all_errors.extend(lint_backend_config_crud_chains(rows))
    all_errors.extend(lint_grouping_structure(parsed, rows))

    if all_errors:
        print("❌ 测试用例校验失败")
        print(f"输入文件: {input_path}")
        print("-" * 80)
        for err in all_errors:
            print(err)
        print("-" * 80)
        print(f"共发现 {len(all_errors)} 个问题")
        return 1

    print("✅ 测试用例校验通过")
    print(f"输入文件: {input_path}")
    print(f"共校验 {len(rows)} 条用例")
    return 0


if __name__ == "__main__":
    sys.exit(main())
