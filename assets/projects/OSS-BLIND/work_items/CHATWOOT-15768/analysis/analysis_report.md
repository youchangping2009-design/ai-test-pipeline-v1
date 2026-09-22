# Analysis Report

## Requirement Summary
- 标题：`CHATWOOT-15768 Conversation filter typed value matching 需求整理`
- 摘要：会话高级筛选必须按自定义属性的真实数据类型生成并匹配筛选值。数字属性应产生数字输入；数值 `{0}` 与布尔值 `{false}` 是有效值，不得被当成空值。客户端会话匹配继续使用严格相等，不应把所有属性统一转换为字符串。
- 主要页面数：0
- 主要展示面数：0

## Reasoning Snapshot
- explicit_rules：15
- implicit_rules：0
- field_constraints：0
- data_source_rules：0
- business_risks：3
- edge_cases：4
- ambiguities：4
- recommended_test_dimensions：7
- coverage_candidates：15

## Top Explicit Rules
- `ER-001` 会话高级筛选必须按自定义属性的真实数据类型生成并匹配筛选值。数字属性应产生数字输入；数值 `{0}` 与布尔值 `{false}` 是有效值，不得被当成空值。客户端会话匹配继续使用严格相等，不应把所有属性统一转换为字符串。
- `ER-002` number 自定义属性的筛选控件和值转换必须保持数值类型。
- `ER-003` 生成请求时只把 `null`、`undefined`、空字符串等真正空值视为空；`0` 和 `false` 必须保留。
- `ER-004` 读取 conversation custom attribute 时不得依赖 truthy 判断。
- `ER-005` 客户端匹配保持严格相等，输入和值的数据类型应在链路前端正确归一。
- `ER-006` 数字属性输入正数和 `{0}` 后，请求及本地匹配均保留 number 类型。
- `ER-007` checkbox 属性为 `{false}` 时仍能被 `equal_to` 命中，并被 `not_equal_to` 排除。
- `ER-008` 属性缺失时不得与 `{0}` 或 `{false}` 混淆。

## Top Implicit Rules

## Key Risks
- `RISK-001` [medium] 历史保存的字符串数字筛选不会自动迁移，可能继续与数字属性严格匹配失败。
- `RISK-002` [medium] JavaScript falsy 语义可能同时影响校验、请求生成和本地列表过滤，需要跨层一致性验证。
- `RISK-003` [medium] inbox ID 类型问题与本次修复共享匹配路径，但属于独立变更。

## Ambiguities
- `AMB-001` 空数组和空对象在正式产品校验中是否都应视为空值？
- `AMB-002` 小数、负数、极大值和科学计数法是否属于 number 属性允许范围？
- `AMB-003` 历史字符串筛选是否需要兼容提示或手工重建指引？
- `AMB-004` Fresh UI verification 在合并前是否完成，PR 描述未给出最终结果。

## Recommended Test Dimensions
- `TD-001` 显式规则逐条验证：需求摘要已给出可追溯规则，后续设计应保持单规则单断言并验证成功与失败结果。
- `TD-002` 异常与失败处理：需求包含明确拒绝或失败语义，需要验证失败状态、错误反馈及副作用隔离。
- `TD-003` 兼容性与回归：需求要求保留既有合法行为或历史关系，需要同时验证变更路径与未变路径。
- `TD-004` 数据一致性与状态保留：需求涉及关系或状态保留，应核对操作前后数据集合而非只看接口成功。
- `TD-005` 输入类型与边界：输入的类型、边界值和协议格式会影响判断结果，需要覆盖合法、非法及临界输入。
- `TD-006` 风险与非功能约束：需求摘要已明确兼容性、性能或一致性风险，需与产品验收规则分层承接。
- `TD-007` 未决项追踪：摘要存在尚未确认的输入或验收口径，后续不得将其自动升级为强制规则。
