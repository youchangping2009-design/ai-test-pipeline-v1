from __future__ import annotations

from typing import Any


BACKEND_CONFIG_PAGES = {
    "小程序banner配置页": "banner",
    "小程序瓷片区配置页": "tile",
    "小程序金刚区配置页": "icon",
    "小程序弹窗配置页": "popup",
}

SELECTION_CONTROL_TYPES = {
    "select",
    "select_single",
    "select_multi",
    "cascader",
    "tree_select",
    "multi_select",
}

DISPLAY_METADATA_FIELD_NAMES = {
    "creator",
    "creator_name",
    "created_by",
    "created_at",
    "create_time",
    "created_time",
    "updated_at",
    "update_time",
    "updated_time",
    "modifier",
    "modifier_name",
    "modified_by",
    "modified_at",
    "operator",
    "operator_name",
    "last_operator",
    "last_modified_by",
    "last_modified_at",
}

DISPLAY_METADATA_KEYWORDS = (
    "创建人",
    "创建时间",
    "创建日期",
    "修改人",
    "修改时间",
    "更新时间",
    "更新人",
    "操作人",
)

DISPLAY_METADATA_DATA_SOURCE_KEYWORDS = (
    "创建该条数据的账号名",
    "创建该条数据时间",
    "数据最新修改时间",
    "最后操作人账号名",
    "最后修改时间",
)


def _strip_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _field_name_tokens(field: dict[str, Any]) -> tuple[str, str]:
    raw_name = _strip_string(field.get("field_name")) or _strip_string(field.get("name"))
    return raw_name, raw_name.lower()


def _field_control_type(field: dict[str, Any]) -> str:
    return (_strip_string(field.get("type")) or _strip_string(field.get("control_type"))).lower()


def is_display_field(field: dict[str, Any]) -> bool:
    raw_name, normalized_name = _field_name_tokens(field)
    if normalized_name in DISPLAY_METADATA_FIELD_NAMES:
        return True

    display = _strip_string(field.get("display")) or _strip_string(field.get("display_name"))
    data_source = _strip_string(field.get("data_source"))
    label_text = " ".join(part for part in (raw_name, display) if part).lower()
    if any(keyword in label_text for keyword in DISPLAY_METADATA_KEYWORDS):
        return True

    lowered_data_source = data_source.lower()
    if any(keyword in lowered_data_source for keyword in DISPLAY_METADATA_DATA_SOURCE_KEYWORDS):
        return True

    return False


def is_selection_source_field(field: dict[str, Any]) -> bool:
    if is_display_field(field):
        return False

    control_type = _field_control_type(field)
    if control_type not in SELECTION_CONTROL_TYPES:
        return False

    has_business_source_signal = any(
        field.get(key) not in ("", None, [])
        for key in ("data_source", "filter", "order_by")
    )
    return has_business_source_signal


def classify_backend_config_field(field: dict[str, Any]) -> str:
    if is_display_field(field):
        return "display_field"
    if is_selection_source_field(field):
        return "selection_source_field"
    return "other_field"


def detect_backend_config_families(image_evidence: dict[str, Any]) -> set[str]:
    families: set[str] = set()
    for image in image_evidence.get("images", []):
        if not isinstance(image, dict):
            continue
        page_name = str(image.get("page_name", "")).strip()
        family = BACKEND_CONFIG_PAGES.get(page_name)
        if family:
            families.add(family)
    return families


def has_backend_config_family_pages(image_evidence: dict[str, Any]) -> bool:
    return bool(detect_backend_config_families(image_evidence))
