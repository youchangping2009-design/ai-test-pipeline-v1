# Testpoints View

- Project: `OSS-BLIND`
- Work Item: `CHATWOOT-15768`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | cross_surface_linkage | 数字自定义属性从输入到匹配保持 number 类型 | number 类型自定义属性的控件值、请求值和客户端匹配值全程保持 number 类型。 | P0 | CP-001 | True |
| TP-002 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | data_persistence | 请求保留 0 和 false 并过滤真正空值 | 筛选请求保留数值 0 和布尔值 false，同时将 null、undefined 和空字符串作为空值排除。 | P0 | CP-002 | True |
| TP-003 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | data_persistence | 属性缺失与显式 0、false 分开匹配 | 客户端读取属性时不把字段缺失等同于 0 或 false，显式 0 和 false 仍按各自值参与匹配。 | P0 | CP-003 | True |
| TP-004 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | data_persistence | 客户端二次筛选使用严格相等匹配 | 客户端仅匹配类型和值都相等的属性，不把字符串与数值等不同类型统一转为字符串比较。 | P0 | CP-004 | True |
| TP-005 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | field_rule | 等于与不等于运算符按严格相等结果筛选 | 等于运算符只命中严格相等值，不等于运算符排除严格相等值并保留不严格相等的会话。 | P0 | CP-005 | True |
| TP-006 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | field_rule | 文本、日期和列表筛选保持既有结果 | 文本、日期和列表类型继续按各自既有类型与运算规则返回正确会话。 | P1 | CP-007 | True |
| TP-007 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | field_rule | 空数组筛选值返回必填错误 | 空数组 `[]` 返回 {VALUE_REQUIRED}，且不生成或发送筛选请求。 | P0 | CP-008 | True |
| TP-008 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | field_rule | 早于当前日期天数输入 0 返回范围错误 | “创建时间”选择“早于当前日期天数”并输入 {0} 时返回 {VALUE_MUST_BE_BETWEEN_1_AND_998}。 | P0 | CP-009 | True |
| TP-009 | 会话列表页 | 高级筛选面板 | 会话高级筛选 | 自定义属性类型化筛选 | field_rule | 空对象筛选值返回必填错误 | 空对象 `{}` 返回 {VALUE_REQUIRED}，且不生成或发送筛选请求。 | P0 | CP-010 | True |
