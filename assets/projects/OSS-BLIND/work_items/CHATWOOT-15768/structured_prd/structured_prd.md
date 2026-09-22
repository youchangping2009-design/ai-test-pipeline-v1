# Structured PRD

## project_info
```json
{
  "project_code": "OSS-BLIND",
  "project_name": "Chatwoot",
  "business_line": "会话高级筛选",
  "prd_source": "inputs/requirement_summary.md",
  "prd_version": "github-pr-15768"
}
```

## requirement_info
```json
{
  "requirement_title": "Conversation filter typed value matching",
  "requirement_background": "会话高级筛选中的自定义属性值需要保持真实数据类型；truthy 判断会错误丢弃 0 和 false，并可能导致客户端二次过滤后的列表与数量不一致。",
  "requirement_goal": "让自定义属性筛选从输入、请求到客户端匹配全程保留类型，正确区分有效 falsy 值、真正空值和缺失属性。",
  "explicit_rules": [
    {
      "rule_id": "CW-R001",
      "rule_text": "number 自定义属性的筛选控件和值转换必须保持 number 类型。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "number 自定义属性",
      "source_scope": "primary_requirement"
    },
    {
      "rule_id": "CW-R002",
      "rule_text": "生成筛选请求时只把 null、undefined、空字符串等真正空值视为空；数值 0 和布尔值 false 是有效值，必须保留。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "filter payload values",
      "source_scope": "primary_requirement",
      "fidelity_points": [
        {
          "constraint_type": "field_constraint",
          "value": "0 和 false 必须保留",
          "must_preserve": true,
          "forbidden_rewrites": ["falsy 值均为空"]
        }
      ]
    },
    {
      "rule_id": "CW-R003",
      "rule_text": "读取 conversation custom attribute 时不得依赖 truthy 判断；缺失属性不得与显式的 0 或 false 混淆。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "conversation custom attribute",
      "source_scope": "primary_requirement"
    },
    {
      "rule_id": "CW-R004",
      "rule_text": "客户端会话匹配继续使用严格相等，输入值与会话属性值不得统一转换为字符串。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "客户端二次匹配",
      "source_scope": "primary_requirement"
    },
    {
      "rule_id": "CW-R005",
      "rule_text": "equal_to 应命中类型和值都相等的会话；not_equal_to 应排除类型和值都相等的会话。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "equal_to 与 not_equal_to",
      "source_scope": "primary_requirement"
    },
    {
      "rule_id": "CW-R006",
      "rule_text": "筛选后的数量徽标与会话列表结果应一致；出现差异时需区分后端返回与客户端二次过滤结果。",
      "rule_type": "state_constraint",
      "priority": "medium",
      "applies_to": "筛选结果展示",
      "source_scope": "context_only"
    },
    {
      "rule_id": "CW-R007",
      "rule_text": "文本、日期、列表等既有筛选类型不得因本次类型化修复回退。",
      "rule_type": "state_constraint",
      "priority": "high",
      "applies_to": "既有筛选类型",
      "source_scope": "primary_requirement"
    },
    {
      "rule_id": "CW-R008",
      "rule_text": "筛选输入为空数组或空对象时属于缺少有效值，输入校验必须返回 VALUE_REQUIRED，且不得进入请求序列化。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "集合型空筛选值",
      "source_scope": "primary_requirement",
      "atomic_assertions": [
        "筛选输入为空数组时返回 VALUE_REQUIRED，且不得进入请求序列化。",
        "筛选输入为空对象时返回 VALUE_REQUIRED，且不得进入请求序列化。"
      ]
    },
    {
      "rule_id": "CW-R009",
      "rule_text": "created_at 使用 days_before 运算符且输入值为 0 时，不得因 0 是有效 falsy 值而绕过日期范围校验，必须返回 VALUE_MUST_BE_BETWEEN_1_AND_998。",
      "rule_type": "data_rule",
      "priority": "high",
      "applies_to": "days_before 日期范围",
      "source_scope": "primary_requirement"
    }
  ],
  "scope": {
    "in_scope": [
      "数字自定义属性的输入与值转换",
      "0 和 false 在校验、请求与客户端匹配链路中的保留",
      "equal_to 与 not_equal_to 严格相等匹配",
      "缺失属性与显式 falsy 值的区分",
      "筛选结果列表与数量一致性"
    ],
    "out_of_scope": [
      "历史字符串型筛选值迁移",
      "把所有属性值转换为字符串",
      "inbox ID 原始类型修复",
      "后端 SQL 过滤语义修改",
      "新增接口字段、数据库迁移或埋点"
    ]
  }
}
```

## pages
```json
[
  {
    "page_name": "会话列表页",
    "page_desc": "打开高级筛选并查看筛选后的会话及数量。",
    "sections": [
      {
        "section_name": "高级筛选面板",
        "section_type": "filter_area",
        "section_desc": "按自定义会话属性类型输入筛选值并选择匹配运算符。",
        "module_name": "会话高级筛选",
        "feature_names": ["自定义属性类型化筛选"],
        "section_rules": [
          "数字属性使用数字输入并保持 number 类型",
          "0 与 false 作为有效值保留",
          "支持 equal_to 与 not_equal_to"
        ],
        "field_refs": ["custom_attribute_type", "filter_operator", "filter_values"],
        "field_rule_table_refs": []
      },
      {
        "section_name": "筛选结果区",
        "section_type": "list_area",
        "section_desc": "展示经过客户端严格相等匹配后的会话列表与数量。",
        "module_name": "会话高级筛选",
        "feature_names": ["自定义属性类型化筛选"],
        "section_rules": [
          "客户端匹配保持严格相等",
          "缺失属性不与 0 或 false 混淆",
          "数量徽标与会话列表结果一致"
        ],
        "field_refs": ["conversation_custom_attribute_value", "result_count"],
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
    "module_name": "会话高级筛选",
    "module_desc": "按自定义属性真实类型构造筛选值，并使用严格相等完成客户端会话匹配。",
    "features": [
      {
        "feature_name": "自定义属性类型化筛选",
        "page_name": "会话列表页",
        "section_name": "高级筛选面板",
        "feature_desc": "保持筛选输入、请求值和会话属性值的类型，正确处理 0、false、真正空值和缺失属性。",
        "actors": ["会话管理用户"],
        "entry_conditions": [
          "已创建 number 或 checkbox/boolean 类型的自定义会话属性",
          "会话列表中存在正数、0、true、false、空值或缺失属性的数据"
        ],
        "rules": [
          {
            "rule_id": "CW-FR001",
            "name": "数字筛选值保持 number 类型",
            "rule_type": "value_constraint",
            "field_name": "filter_values",
            "condition": "custom_attribute_type=number",
            "formats": ["number"],
            "rule_text": "数字属性使用数字输入，进入请求和客户端匹配的值保持 number 类型。"
          },
          {
            "rule_id": "CW-FR002",
            "name": "保留有效 falsy 值",
            "rule_type": "value_constraint",
            "field_name": "filter_values",
            "allowed_values": ["0", "false"],
            "rule_text": "0 和 false 不得按空值丢弃。"
          },
          {
            "rule_id": "CW-FR003",
            "name": "区分空值与缺失属性",
            "rule_type": "value_constraint",
            "target": "conversation_custom_attribute_value",
            "condition": "读取会话自定义属性",
            "rule_text": "null、undefined、空字符串等真正空值与显式 0、false 分开处理，属性缺失不得等同于 0 或 false。"
          },
          {
            "rule_id": "CW-FR004",
            "name": "严格相等匹配",
            "rule_type": "value_constraint",
            "target": "client_side_match",
            "condition": "执行客户端会话匹配",
            "rule_text": "比较类型和值，不把全部属性统一转为字符串。"
          },
          {
            "rule_id": "CW-FR005",
            "name": "运算符匹配语义",
            "rule_type": "value_constraint",
            "field_name": "filter_operator",
            "allowed_values": ["equal_to", "not_equal_to"],
            "rule_text": "equal_to 命中严格相等值，not_equal_to 排除严格相等值。"
          },
          {
            "rule_id": "CW-FR006",
            "name": "列表与数量一致",
            "rule_type": "display_constraint",
            "target": "result_count",
            "condition": "筛选结果展示完成",
            "rule_text": "数量徽标与最终展示的会话列表结果一致。"
          }
        ],
        "fields": [
          {
            "name": "custom_attribute_type",
            "display_name": "自定义属性类型",
            "type": "attribute_definition",
            "data_type": "string",
            "required": false,
            "editable": false,
            "enum_values": ["number", "checkbox/boolean", "text", "date", "list"]
          },
          {
            "name": "filter_operator",
            "display_name": "筛选运算符",
            "type": "select_single",
            "data_type": "string",
            "required": false,
            "editable": true,
            "enum_values": ["equal_to", "not_equal_to"]
          },
          {
            "name": "filter_values",
            "display_name": "筛选值",
            "type": "dynamic_input",
            "data_type": "number_or_boolean_or_existing_type",
            "required": false,
            "editable": true,
            "formats": ["number 属性保持 number", "checkbox/boolean 属性保持 boolean"]
          },
          {
            "name": "conversation_custom_attribute_value",
            "display_name": "会话自定义属性值",
            "type": "conversation_data",
            "data_type": "typed_value",
            "required": false,
            "editable": false
          },
          {
            "name": "result_count",
            "display_name": "筛选结果数量",
            "type": "count_badge",
            "data_type": "integer",
            "required": false,
            "editable": false,
            "min": 0,
            "integer_only": true
          }
        ],
        "field_definitions": [],
        "field_rules": [
          {
            "rule_id": "CW-FIELD-001",
            "field_name": "filter_values",
            "display_name": "筛选值",
            "rule_text": "number 属性输入值保持 number 类型，0 与 false 是有效值并在请求中保留。",
            "rule_type": "format_constraint",
            "expected_effects": [
              "请求 values 保留实际数据类型",
              "0 和 false 不被空值校验丢弃"
            ],
            "must_cover": true
          },
          {
            "rule_id": "CW-FIELD-002",
            "field_name": "conversation_custom_attribute_value",
            "display_name": "会话自定义属性值",
            "rule_text": "读取属性时区分字段缺失、真正空值、0 和 false。",
            "rule_type": "effect_constraint",
            "expected_effects": [
              "0 与 false 可参与严格相等匹配",
              "缺失属性不误命中 0 或 false"
            ],
            "must_cover": true
          }
        ],
        "field_rule_tables": [],
        "visible_elements": ["高级筛选面板", "筛选运算符", "类型化筛选值输入", "会话列表", "数量徽标"],
        "interactive_entries": ["打开高级筛选", "选择自定义属性", "选择 equal_to 或 not_equal_to", "提交筛选"],
        "abnormal_scenarios": [
          "显式 0 被误判为空值",
          "显式 false 被误判为空值",
          "缺失属性被误判为 0 或 false",
          "类型不同但字符串表示相同的值被错误匹配"
        ],
        "boundary_scenarios": [
          "null、undefined 与空字符串按真正空值处理",
          "空数组和空对象的正式校验语义待确认",
          "小数、负数、极大值和科学计数法的 number 允许范围待确认",
          "历史字符串筛选值不自动迁移"
        ],
        "dependencies": [
          "POST /api/v1/accounts/:id/conversations/filter",
          "custom attribute 定义类型",
          "conversation 实际自定义属性值"
        ]
      }
    ]
  }
]
```

## flows
```json
[
  {
    "flow_id": "CW-FLOW-001",
    "flow_name": "自定义属性类型化会话筛选",
    "flow_type": "main_flow",
    "business_goal": "按自定义属性真实类型筛选会话，并保持最终列表与数量一致。",
    "trigger": "用户在会话列表打开高级筛选并提交自定义属性条件",
    "preconditions": [
      "已存在具有明确数据类型的自定义会话属性",
      "会话数据包含可用于匹配的属性值"
    ],
    "steps": [
      {
        "step_no": 1,
        "step_name": "构造类型化筛选值",
        "step_type": "operation",
        "module_name": "会话高级筛选",
        "feature_name": "自定义属性类型化筛选",
        "actor": "会话管理用户",
        "action": "选择自定义属性和运算符并输入筛选值",
        "input_data": ["custom_attribute_type", "filter_operator", "filter_values"],
        "expected_result": "数字属性生成 number 值，0 与 false 作为有效值保留",
        "rule_references": ["CW-R001", "CW-R002"],
        "is_key_checkpoint": true
      },
      {
        "step_no": 2,
        "step_name": "提交筛选请求",
        "step_type": "operation",
        "module_name": "会话高级筛选",
        "feature_name": "自定义属性类型化筛选",
        "actor": "系统",
        "action": "向会话筛选接口提交包含类型化 values 的筛选条件",
        "input_data": ["POST /api/v1/accounts/:id/conversations/filter", "filter payload values"],
        "expected_result": "请求不因 truthy 判断丢弃 0 或 false",
        "rule_references": ["CW-R002"],
        "is_key_checkpoint": true
      },
      {
        "step_no": 3,
        "step_name": "执行客户端严格匹配",
        "step_type": "data_validation",
        "module_name": "会话高级筛选",
        "feature_name": "自定义属性类型化筛选",
        "actor": "系统",
        "action": "读取会话自定义属性并按 equal_to 或 not_equal_to 执行严格相等匹配",
        "expected_result": "0、false、真正空值和缺失属性被正确区分，类型不同的值不因字符串化而误匹配",
        "checkpoints": [
          "equal_to 仅命中类型和值相等的会话",
          "not_equal_to 排除类型和值相等的会话"
        ],
        "rule_references": ["CW-R003", "CW-R004", "CW-R005"],
        "is_key_checkpoint": true
      },
      {
        "step_no": 4,
        "step_name": "展示筛选结果",
        "step_type": "system_response",
        "module_name": "会话高级筛选",
        "feature_name": "自定义属性类型化筛选",
        "actor": "系统",
        "action": "展示最终会话列表与数量徽标",
        "expected_result": "数量徽标与最终展示的会话列表结果一致",
        "rule_references": ["CW-R006"],
        "is_key_checkpoint": true
      }
    ],
    "postconditions": [
      "最终会话列表符合类型化严格匹配条件",
      "筛选结果数量与列表一致"
    ],
    "success_criteria": [
      "number 属性的输入和请求值保持 number 类型",
      "0 和 false 未被空值判断丢弃",
      "缺失属性不误命中 0 或 false",
      "equal_to 与 not_equal_to 的严格相等语义正确",
      "文本、日期、列表等既有筛选类型无回退"
    ],
    "related_modules": ["会话高级筛选"],
    "priority": "P0",
    "tags": ["typed-value", "falsy-value", "strict-equality"]
  }
]
```
