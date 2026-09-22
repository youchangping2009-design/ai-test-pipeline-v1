# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | CW-R001 | field_constraint | testable | generate_acceptance_example | confirmed | number 自定义属性的筛选控件和值转换必须保持 number 类型。 | 可直接验证控件输入、请求 payload 和客户端匹配值的数据类型。 |
| TG-002 | CW-R002 | field_constraint | testable | generate_acceptance_example | confirmed | 生成筛选请求时只把 null、undefined、空字符串等真正空值视为空；数值 0 和布尔值 false 是有效值，必须保留。 | 0、false 与明确空值可分别构造并检查请求值是否保留。 |
| TG-003 | CW-R003 | product_behavior | testable | generate_acceptance_example | confirmed | 读取 conversation custom attribute 时不得依赖 truthy 判断；缺失属性不得与显式的 0 或 false 混淆。 | 可准备缺失、0 和 false 三类会话并观察匹配集合。 |
| TG-004 | CW-R004 | product_behavior | testable | generate_acceptance_example | confirmed | 客户端会话匹配继续使用严格相等，输入值与会话属性值不得统一转换为字符串。 | 可使用字符串与数值表示相同但类型不同的数据验证严格相等。 |
| TG-005 | CW-R005 | product_behavior | testable | generate_acceptance_example | confirmed | equal_to 应命中类型和值都相等的会话；not_equal_to 应排除类型和值都相等的会话。 | 两个运算符均有明确可观察的包含或排除结果。 |
| TG-006 | CW-R006 | technical_background | out_of_scope | out_of_scope | confirmed | 筛选后的数量徽标与会话列表结果应一致；出现差异时需区分后端返回与客户端二次过滤结果。 | 该数量徽标问题仅是关联 issue 背景，当前 PR 的直接变更不包含此验收范围。 |
| TG-007 | CW-R007 | product_behavior | testable | generate_acceptance_example | confirmed | 文本、日期、列表等既有筛选类型不得因本次类型化修复回退。 | 可用既有筛选类型执行回归并检查结果。 |
| TG-008 | CW-FR001 | field_constraint | testable | skip_case | confirmed | 数字属性使用数字输入，进入请求和客户端匹配的值保持 number 类型。 | 与 CW-R001 的 number 类型规则重复。 |
| TG-009 | CW-FR002 | field_constraint | testable | skip_case | confirmed | 0 和 false 不得按空值丢弃。 | 与 CW-R002 的有效 falsy 值规则重复。 |
| TG-010 | CW-FR003 | product_behavior | testable | skip_case | confirmed | null、undefined、空字符串等真正空值与显式 0、false 分开处理，属性缺失不得等同于 0 或 false。 | 与 CW-R002、CW-R003 的空值和缺失值规则重复。 |
| TG-011 | CW-FR004 | product_behavior | testable | skip_case | confirmed | 比较类型和值，不把全部属性统一转为字符串。 | 与 CW-R004 的严格相等规则重复。 |
| TG-012 | CW-FR005 | product_behavior | testable | skip_case | confirmed | equal_to 命中严格相等值，not_equal_to 排除严格相等值。 | 与 CW-R005 的运算符规则重复。 |
| TG-013 | CW-FR006 | technical_background | out_of_scope | out_of_scope | confirmed | 数量徽标与最终展示的会话列表结果一致。 | 与 context-only 的 CW-R006 相同，仅保留关联背景，不生成本工作项验收。 |
| TG-014 | CW-FIELD-001 | field_constraint | testable | skip_case | confirmed | number 属性输入值保持 number 类型，0 与 false 是有效值并在请求中保留。 | 与 CW-R001、CW-R002 的类型和值保留规则重复。 |
| TG-015 | CW-FIELD-002 | field_constraint | testable | skip_case | confirmed | 读取属性时区分字段缺失、真正空值、0 和 false。 | 与 CW-R003 的缺失值区分规则重复。 |
| TG-016 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 历史保存的字符串数字筛选不会自动迁移，可能继续与数字属性严格匹配失败。 | 历史值迁移明确不在范围，仅记录兼容性风险。 |
| TG-017 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | JavaScript falsy 语义可能同时影响校验、请求生成和本地列表过滤，需要跨层一致性验证。 | 该项作为跨层风险记录，正式行为已由 CW-R001 至 CW-R006 承接。 |
| TG-018 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | inbox ID 类型问题与本次修复共享匹配路径，但属于独立变更。 | 该问题属于独立变更，不得混入本次产品验收。 |
| TG-019 | CW-R008 | field_constraint | testable | generate_acceptance_example | confirmed | 筛选输入为空数组或空对象时属于缺少有效值，输入校验必须返回 VALUE_REQUIRED，且不得进入请求序列化。 | 可分别提交空数组和空对象，检查输入校验错误及请求未发送。 |
| TG-020 | CW-R009 | field_constraint | testable | generate_acceptance_example | confirmed | created_at 使用 days_before 运算符且输入值为 0 时，不得因 0 是有效 falsy 值而绕过日期范围校验，必须返回 VALUE_MUST_BE_BETWEEN_1_AND_998。 | 可构造 created_at/days_before/0 组合并检查精确范围错误。 |
