#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any


DISPLAY_SIGNALS = ("展示", "隐藏", "可见", "换行", "排序", "候选项来自")
HARD_SIGNALS = ("必填", "必传", "不能为空", "不可保存", "不能保存", "上限", "最大", "必须", "大于")


def humanize_testcase_copy(text: str) -> str:
    result = str(text).strip()
    replacements = (
        ("not_equal_to", "不等于"),
        ("equal_to", "等于"),
        ("不会返回连接成功", "不会返回已建立的连接"),
        ("原有成功行为不回退", "原有可建立连接行为不回退"),
        ("成功创建的全部礼品卡", "本次新建的全部礼品卡"),
        ("判定本次批量创建成功", "判定本次批量创建处于无错误完成状态"),
        ("的成功结果和标签关系行为保持不变", "的既有返回结果和标签关系行为保持不变"),
    )
    for source, target in replacements:
        result = result.replace(source, target)
    return result


def _field_labels(structured_prd: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    labels: dict[tuple[str, str, str], str] = {}
    for module in structured_prd.get("modules", []) or []:
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []) or []:
            feature_name = str(feature.get("feature_name", "")).strip()
            for field in feature.get("fields", []) or []:
                field_name = str(field.get("field_name", "")).strip()
                if field_name:
                    labels[(module_name, feature_name, field_name)] = str(
                        field.get("display_name") or field_name
                    ).strip()
    return labels


def _global_field_labels(labels: dict[tuple[str, str, str], str]) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    for (_, _, field_name), display_name in labels.items():
        candidates.setdefault(field_name, set()).add(display_name)
    return {
        field_name: next(iter(display_names))
        for field_name, display_names in candidates.items()
        if len(display_names) == 1
    }


def build_source_index(
    structured_prd: dict[str, Any],
    coverage_matrix: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    labels = _field_labels(structured_prd)
    global_labels = _global_field_labels(labels)
    for module in structured_prd.get("modules", []) or []:
        module_name = str(module.get("module_name", "")).strip()
        for feature in module.get("features", []) or []:
            feature_name = str(feature.get("feature_name", "")).strip()
            page_name = str(feature.get("page_name", "")).strip()
            section_name = str(feature.get("section_name", "")).strip()
            for collection in ("rules", "field_rules"):
                for rule in feature.get(collection, []) or []:
                    if not isinstance(rule, dict):
                        continue
                    rule_id = str(rule.get("rule_id", "")).strip()
                    if not rule_id:
                        continue
                    field_name = str(rule.get("field_name", "")).strip()
                    index[rule_id] = {
                        **rule,
                        "page_name": page_name,
                        "section_name": section_name,
                        "module_name": module_name,
                        "feature_name": feature_name,
                        "display_name": str(rule.get("display_name") or labels.get((module_name, feature_name, field_name), field_name)).strip(),
                    }
    for entry in coverage_matrix.get("entries", []) or []:
        if not isinstance(entry, dict):
            continue
        coverage_id = str(entry.get("coverage_id", "")).strip()
        if coverage_id:
            index[coverage_id] = {
                **entry,
                "rule_text": str(entry.get("title", "")).strip(),
                "display_name": global_labels.get(
                    str(entry.get("field_name", "")).strip(),
                    str(entry.get("field_name", "")).strip(),
                ),
            }
    return index


def source_descriptor(plan: dict[str, Any], source_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    for source_id in [*(plan.get("source_rule_ids", []) or []), *(plan.get("source_coverage_ids", []) or [])]:
        descriptor = source_index.get(str(source_id).strip())
        if descriptor:
            return descriptor
    return {}


def human_rule_detail(plan: dict[str, Any], descriptor: dict[str, Any]) -> str:
    label = str(descriptor.get("display_name", "")).strip()
    planned_assertions = [
        str(item).strip().rstrip("。")
        for item in descriptor.get("planned_assertions", []) or []
        if str(item).strip()
    ]
    rule_text = str(
        (planned_assertions[0] if planned_assertions else "")
        or descriptor.get("rule_text")
        or descriptor.get("source_text")
        or ""
    ).strip().rstrip("。")
    rule_text = rule_text.replace("`", "")
    formats = [str(item).strip() for item in descriptor.get("formats", []) or [] if str(item).strip()]
    data_source = str(descriptor.get("data_source", "")).strip()
    visible_when = str(descriptor.get("visible_when", "")).strip()

    if data_source and label:
        return f"“{label}”候选项来自{data_source}"
    if visible_when:
        return f"“{label}”{visible_when}" if label and label not in visible_when else visible_when
    if formats and label:
        detail = "；".join(formats)
        if detail == "数值限制大于0.00":
            return f"“{label}”必须填写大于{{0.00}}的数值"
        if "正整数" in detail and "1000" in detail:
            return f"“{label}”只能填写不大于{{1000}}的正整数"
        if "正整数" in detail and "200" in detail:
            return f"“{label}”只能填写不大于{{200}}的正整数"
        if "天最大370" in detail or "天数最大370" in detail:
            return f"“{label}”天数最大{{370}}、小时最大{{23}}且不能同时为{{0}}"
        if "换行展示" in detail:
            return f"“{label}”超过一行时在C端换行展示"
        return f"“{label}”{detail}"
    if label and label in rule_text and f"“{label}”" not in rule_text:
        return rule_text.replace(label, f"“{label}”")
    if label and rule_text and label not in rule_text:
        return f"“{label}”{rule_text}"
    if rule_text and not re.search(r"[a-z_]+\s*;", rule_text):
        return rule_text
    title = re.sub(r"^(约束判定|读侧展示|业务结果|提示展示|后台任务|跨端联动)[:：]", "", str(plan.get("title", ""))).strip()
    return re.sub(r"（场景\d+）$", "", title).strip()


def is_display_only(descriptor: dict[str, Any], detail: str) -> bool:
    rule_type = str(descriptor.get("rule_type", "")).strip()
    if rule_type in {"conditional_visibility", "conditional_visibility_rule", "display_constraint"}:
        return True
    return any(signal in detail for signal in DISPLAY_SIGNALS) and not any(
        signal in detail for signal in HARD_SIGNALS
    ) and re.search(r"超过\s*\d+", detail) is None


def normalized_plan_semantics(
    plan: dict[str, Any],
    descriptor: dict[str, Any],
    gate: dict[str, Any] | None = None,
) -> dict[str, str]:
    detail = human_rule_detail(plan, descriptor)
    classification = str((gate or {}).get("classification", "")).strip()
    current_type = str(plan.get("case_type", "")).strip()
    if classification == "soft_prompt" or current_type == "prompt_display":
        case_type = "prompt_display"
    elif classification == "backend_job" or current_type == "backend_job":
        case_type = "backend_job"
    elif classification == "linkage" or current_type == "linkage":
        case_type = "linkage"
    elif current_type in {"data_persistence", "permission_scope", "risk_hardening"}:
        case_type = current_type
    elif is_display_only(descriptor, detail):
        case_type = "ui_display"
    elif current_type in {
        "field_constraint",
        "save_block",
        "ui_display",
    }:
        case_type = current_type
    elif any(signal in detail for signal in HARD_SIGNALS):
        case_type = "save_block"
    else:
        case_type = "field_constraint"

    if case_type == "ui_display":
        page_name = str(plan.get("page_name", "")).strip()
        verification_side = "C端读侧" if "C端" in detail or "后台" not in page_name else "B端写侧"
    elif case_type in {"save_block", "field_constraint", "prompt_display"}:
        verification_side = "B端写侧"
    else:
        verification_side = str(plan.get("verification_side", "")).strip()

    detail = detail.replace("增加未配置提示", "增加未配置状态说明")
    detail = detail.replace("点击增加一条宣传配置", "通过【增加一条】新增宣传配置")
    detail = detail.replace("配置第5个特殊区商品时展示图片指定提示且不可保存", "配置第{5}个特殊区商品时不可保存")
    title = f"验证{detail}"
    if case_type == "save_block":
        assertion = f"违反{detail}时，系统阻止保存并保留原配置。"
    elif case_type == "prompt_display":
        assertion = f"页面展示与{detail}对应的说明，其中建议内容不作为提交拦截条件。"
    elif case_type == "backend_job":
        assertion = f"后台任务执行后可观察到：{detail}。"
    elif case_type == "linkage":
        assertion = f"触发条件后，各验证端分别出现以下结果：{detail}。"
    else:
        assertion = f"页面可直接观察到：{detail}。"
    return {
        "detail": detail,
        "case_type": case_type,
        "verification_side": verification_side,
        "title": title,
        "assertion": assertion,
    }


def direct_case_steps_expected(
    plan: dict[str, Any],
    semantics: dict[str, str],
    descriptor: dict[str, Any],
    acceptance_example: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    page_name = str(plan.get("page_name", "")).strip()
    section_name = str(plan.get("section_name", "")).strip()
    detail = semantics["detail"]
    case_type = semantics["case_type"]
    label = str(descriptor.get("display_name", "")).strip()
    field = f"“{label}”" if label else "目标配置项"
    location = f"[{page_name}]的{section_name}" if section_name else f"[{page_name}]"
    plan_expected = [
        humanize_testcase_copy(item.strip())
        for item in re.split(r"[；;\n]+", str(plan.get("assertion", "")))
        if item.strip()
    ]

    if acceptance_example:
        given = [humanize_testcase_copy(item) for item in acceptance_example.get("given", []) if str(item).strip()]
        when = [humanize_testcase_copy(item) for item in acceptance_example.get("when", []) if str(item).strip()]
        then = [humanize_testcase_copy(item) for item in acceptance_example.get("then", []) if str(item).strip()]
        if given and when and then:
            terminal_keywords = ("状态", "生效", "可见", "完成", "流转", "回传", "展示", "进入游戏")
            if case_type == "linkage" and not any(
                keyword in " ".join(then) for keyword in terminal_keywords
            ):
                verification_side = str(plan.get("verification_side", "")).strip()
                if any(token in verification_side for token in ("API", "数据层")):
                    then.append("最终关系状态可通过接口响应与数据查询核对。")
                elif "服务端" in verification_side:
                    then.append("最终连接处理状态可通过 driver 与网络调用记录核对。")
                else:
                    then.append("最终处理状态可在对应列表或响应结果中核对。")
            # Case Plan 是正式用例的设计真源；Acceptance Example 提供可执行的
            # Given/When/Then 上下文，但不能遮蔽后续反馈写入的计划断言。
            return given, when, plan_expected or then

    if case_type == "ui_display":
        steps = [f"准备满足“{detail}”的上游配置或数据", f"进入{location}", f"观察{field}对应的页面结果"]
        expected = [f"{location}可直接观察到：{detail}"]
    elif case_type == "prompt_display":
        steps = [f"进入{location}", f"定位{field}控件", "查看控件旁的数量、格式、大小及建议尺寸说明"]
        expected = [f"控件旁展示与“{detail}”对应的说明", "建议尺寸仅作辅助说明，不会单独阻止提交"]
    elif case_type == "backend_job":
        steps = [f"在{location}配置满足触发条件的数据", "触发或等待后台任务执行", "查询任务结果、通知记录及C端状态"]
        expected = [f"后台任务执行后可观察到：{detail}", "任务结果、通知记录与C端状态分别可核对"]
    elif case_type == "linkage":
        steps = [f"在{location}准备并保存触发条件", "触发对应业务动作", "分别检查B端记录、服务端处理结果和C端展示"]
        expected = [f"触发后可观察到：{detail}", "各验证端最终状态来自同一次配置或业务事件"]
    elif case_type == "save_block":
        if "大于{0.00}" in detail:
            action = f"向{field}输入{{0.00}}"
        elif "不大于{1000}" in detail:
            action = f"向{field}输入{{1001}}"
        elif "不大于{200}" in detail:
            action = f"向{field}输入{{201}}"
        elif "最大{370}" in detail:
            action = f"将{field}天数设置为{{371}}"
        elif "最多" in detail and "4" in detail:
            action = "尝试保存第{5}个特殊区商品"
        elif "20个字符" in detail:
            action = f"向{field}输入{{21}}个字符"
        elif "必填" in detail or "必传" in detail:
            action = f"保持{field}为空"
        else:
            action = f"按“{detail}”构造一个违反限制的明确输入"
        steps = [f"进入{location}", action, "点击【保存】并观察校验反馈"]
        expected = [f"系统阻止本次保存，原配置不发生变化", f"页面反馈当前输入违反：{detail}"]
    else:
        steps = [f"进入{location}", f"按“{detail}”准备一个合法值或配置", "点击【保存】后重新打开该记录"]
        expected = [f"保存后的页面结果明确体现：{detail}", f"重新打开记录后{field}仍显示本次保存值"]
    if plan_expected:
        expected = plan_expected
    return [f"已进入{location}并准备完成该规则所需数据"], steps, expected


def testcase_type(case_type: str, detail: str) -> str:
    if case_type == "save_block":
        return "异常"
    if case_type == "linkage":
        return "流程验证"
    if case_type == "backend_job":
        return "状态流转"
    if case_type == "data_persistence":
        return "数据校验"
    if case_type == "permission_scope":
        return "权限"
    if case_type == "field_constraint" and any(
        token in detail for token in ("拒绝", "失败", "错误", "不得判为成功", "不允许")
    ):
        return "异常"
    if case_type == "field_constraint" and any(
        token in detail for token in ("上限", "最大", "大于", "长度", "边界")
    ):
        return "边界"
    return "功能"


def rewrite_case_id_type(case_id: str, test_type: str) -> str:
    type_codes = {
        "功能": "FN",
        "边界": "BD",
        "异常": "AB",
        "权限": "PM",
        "流程验证": "FL",
        "状态流转": "ST",
        "数据校验": "DV",
    }
    code = type_codes[test_type]
    return re.sub(r"-(?:FN|BD|AB|PM|FL|ST|DV)-(\d{3,})$", rf"-{code}-\1", case_id)


def semantic_signature(plan: dict[str, Any], semantics: dict[str, str]) -> tuple[str, str, str, str]:
    detail = re.sub(r"[\s：:，,。；;（）()]", "", semantics["detail"])
    return (
        str(plan.get("page_name", "")).strip(),
        str(plan.get("section_name", "")).strip(),
        semantics["case_type"],
        detail,
    )
