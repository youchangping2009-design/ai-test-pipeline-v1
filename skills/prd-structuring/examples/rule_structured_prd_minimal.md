# Structured PRD

## project_info
```json
{
  "project_code": "DEMO",
  "project_name": "规则型结构最小示例",
  "business_line": "Schema Validation",
  "prd_source": "sample://rule-structured-prd-minimal-md",
  "prd_version": "phase-2"
}
```

## requirement_info
```json
{
  "requirement_title": "规则型 structured_prd Markdown 编译示例",
  "requirement_background": "用于验证 structured_prd.md -> structured_prd.json 过程中的规则保真。",
  "requirement_goal": "验证条件展示、条件必填、条件只读 / 可编辑、数值边界、数据源过滤 / 排序可稳定进入 JSON。",
  "scope": {
    "in_scope": [
      "markdown compile",
      "rule normalization"
    ],
    "out_of_scope": []
  }
}
```

## pages
```json
[
  {
    "page_name": "示例配置页",
    "page_desc": "用于校验 markdown 编译保真的最小页面。",
    "sections": [
      {
        "section_name": "添加弹窗",
        "section_type": "edit_modal",
        "section_desc": "规则型字段定义示例",
        "module_name": "示例配置模块",
        "feature_names": [
          "规则型字段示例"
        ],
        "section_rules": [],
        "field_refs": [
          "activity_name",
          "display_days",
          "selected_activity"
        ],
        "field_rule_table_refs": []
      }
    ]
  }
]
```

## modules
```json
[
  {
    "module_name": "示例配置模块",
    "module_desc": "演示 markdown 编译后的规则型字段结构。",
    "features": [
      {
        "feature_name": "规则型字段示例",
        "page_name": "示例配置页",
        "section_name": "添加弹窗",
        "feature_desc": "使用 fields[] 与对象版 rules[] 承载规则结构。",
        "actors": [
          "后台运营"
        ],
        "entry_conditions": [
          "进入示例配置页并打开添加弹窗"
        ],
        "rules": [
          {
            "rule_id": "RULE-001",
            "name": "展示天数字段按展示类型联动显示",
            "rule_type": "conditional_visibility",
            "field_name": "display_days",
            "condition": "display_type=after_days"
          },
          {
            "rule_id": "RULE-002",
            "name": "展示天数字段按展示类型联动必填",
            "rule_type": "conditional_required",
            "field_name": "display_days",
            "required_when": "display_type=after_days"
          },
          {
            "rule_id": "RULE-003",
            "name": "活动链接在活动中心场景只读",
            "rule_type": "conditional_readonly",
            "field_name": "link_url",
            "readonly_when": "jump_type=activity_center"
          }
        ],
        "fields": [
          {
            "name": "activity_name",
            "type": "text_input",
            "data_type": "string",
            "required": true,
            "editable": true,
            "default": "",
            "max_length": 20,
            "formats": [
              "trimmed_string"
            ]
          },
          {
            "name": "display_days",
            "type": "number_input",
            "data_type": "integer",
            "required": false,
            "editable": true,
            "default": null,
            "required_when": "display_type=after_days",
            "visible_when": "display_type=after_days",
            "editable_when": "display_type=after_days",
            "readonly_when": "display_type!=after_days",
            "min": 1,
            "max": 99,
            "integer_only": true
          },
          {
            "name": "selected_activity",
            "type": "select_single",
            "data_type": "string",
            "required": true,
            "editable": true,
            "default": "",
            "data_source": "活动中心渠道=小程序的活动",
            "filter": "状态=发布",
            "display": "id+活动名称",
            "order_by": "按活动创建时间倒序"
          }
        ],
        "field_definitions": [],
        "field_rules": [],
        "field_rule_tables": [],
        "visible_elements": [
          "活动名称输入框",
          "展示天数输入框",
          "选择活动下拉框"
        ],
        "interactive_entries": [
          "点击保存"
        ],
        "abnormal_scenarios": [],
        "boundary_scenarios": [],
        "dependencies": []
      }
    ]
  }
]
```

## flows
```json
[
  {
    "flow_id": "FLOW-001",
    "flow_name": "示例配置提交流程",
    "flow_type": "main_flow",
    "business_goal": "验证 markdown 编译后的规则型字段结构可被保存。",
    "related_modules": [
      "示例配置模块"
    ],
    "steps": [
      {
        "step_no": 1,
        "step_name": "打开添加弹窗",
        "action": "打开示例配置页添加弹窗",
        "expected_result": "添加弹窗展示规则型字段",
        "module_name": "示例配置模块",
        "feature_name": "规则型字段示例"
      },
      {
        "step_no": 2,
        "step_name": "填写并保存配置",
        "action": "填写活动名称、展示天数和选择活动并保存",
        "expected_result": "规则型字段与规则对象被稳定编译到 JSON",
        "module_name": "示例配置模块",
        "feature_name": "规则型字段示例"
      }
    ],
    "success_criteria": [
      "required_when / visible_when / readonly_when / 边界 / 过滤 / 排序均进入 structured_prd.json"
    ],
    "priority": "P1",
    "tags": [
      "schema-demo"
    ]
  }
]
```
