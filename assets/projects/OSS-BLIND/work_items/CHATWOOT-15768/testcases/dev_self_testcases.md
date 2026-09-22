# 开发自测用例

# 页面：会话列表页

## 板块：高级筛选面板

| 用例编号 | 所属模块 | 所属功能点 | 用例标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 | 标签 | 测试类型 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OSS-BLIND-CONVERSATION-FILTER-WEB-FL-001 | 会话高级筛选 | 自定义属性类型化筛选 | 数字自定义属性从输入到匹配保持 number 类型 | 会话存在 number 类型自定义属性，用户在[会话列表页]的高级筛选中选择该属性。 | 1. 用户输入数字并应用筛选。 | 1. 筛选控件产生 number 类型的值。<br>2. 筛选请求和客户端匹配使用的值均保持 number 类型。<br>3. 最终处理状态可在对应列表或响应结果中核对。 | P0 | AI-API用例,AI-UI用例,开发必测,测试必测 | 流程验证 | 来源 CasePlan：CP-001；来源 Flow：CP-001；来源 Acceptance：AE-001；来源 Rule：CW-R001；来源coverage：COV-EX-0006 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-DV-002 | 会话高级筛选 | 自定义属性类型化筛选 | 请求保留 0 和 false 并过滤真正空值 | 分别准备筛选值 0、false、null、undefined 和空字符串。 | 1. 前端生成会话筛选请求。 | 1. 数值 0 和布尔值 false 均保留在请求值中。<br>2. null、undefined 和空字符串按空值处理，不作为有效筛选值发送。 | P0 | AI-API用例,AI-UI用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-002；来源 Acceptance：AE-002；来源 Rule：CW-R002；来源coverage：COV-EX-0007 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-DV-003 | 会话高级筛选 | 自定义属性类型化筛选 | 属性缺失与显式 0、false 分开匹配 | 会话集合分别包含属性缺失、属性值为数值 0、属性值为布尔值 false 的记录。 | 1. 客户端读取自定义属性并执行筛选匹配。 | 1. 属性缺失的会话不会被当作值为 0 或 false。<br>2. 属性值为 0 或 false 的会话仍可按各自显式值参与匹配。 | P0 | AI-UI用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-003；来源 Acceptance：AE-003；来源 Rule：CW-R003；来源coverage：COV-EX-0008 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-DV-004 | 会话高级筛选 | 自定义属性类型化筛选 | 客户端二次筛选使用严格相等匹配 | 会话属性包含数值 0 和字符串 `0` 等值相同但类型不同的数据。 | 1. 客户端使用数值 0 执行二次筛选匹配。 | 1. 仅数值与类型都相等的会话被视为匹配。<br>2. 字符串 `0` 不会因统一字符串化而与数值 0 匹配。 | P0 | AI-UI用例,开发必测,测试必测 | 数据校验 | 来源 CasePlan：CP-004；来源 Acceptance：AE-004；来源 Rule：CW-R004；来源coverage：COV-EX-0009 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-FN-001 | 会话高级筛选 | 自定义属性类型化筛选 | 等于与不等于运算符按严格相等结果筛选 | 会话集合同时包含与筛选值类型和值都相等、仅文本表示相同但类型不同的属性值。 | 1. 用户分别使用 等于 和 不等于 应用同一筛选值。 | 1. 等于 只命中类型和值都相等的会话。<br>2. 不等于 排除类型和值都相等的会话，并保留不严格相等的会话。 | P0 | AI-UI用例,开发必测,测试必测 | 功能 | 来源 CasePlan：CP-005；来源 Acceptance：AE-005；来源 Rule：CW-R005；来源coverage：COV-EX-0010 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-AB-001 | 会话高级筛选 | 自定义属性类型化筛选 | 空数组筛选值返回必填错误 | 准备空数组 `[]` 作为筛选输入。 | 1. 用户应用会话高级筛选。 | 1. 输入返回错误值 {VALUE_REQUIRED}。<br>2. 输入校验失败后不生成或发送筛选请求。 | P0 | AI-API用例,AI-UI用例,开发必测,测试必测 | 异常 | 来源 CasePlan：CP-008；来源 Acceptance：AE-008；来源 Rule：CW-R008；来源coverage：COV-EX-0013 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-AB-002 | 会话高级筛选 | 自定义属性类型化筛选 | 早于当前日期天数输入 0 返回范围错误 | “创建时间”筛选条件选择“早于当前日期天数”，输入值为 {0}。 | 1. 用户应用会话高级筛选。 | 1. 系统返回错误值 {VALUE_MUST_BE_BETWEEN_1_AND_998}。<br>2. 数值 {0} 不会因空值保留逻辑而绕过日期范围校验。 | P0 | AI-UI用例,开发必测,测试必测 | 异常 | 来源 CasePlan：CP-009；来源 Acceptance：AE-009；来源 Rule：CW-R009；来源coverage：COV-EX-0015 |
| OSS-BLIND-CONVERSATION-FILTER-WEB-AB-003 | 会话高级筛选 | 自定义属性类型化筛选 | 空对象筛选值返回必填错误 | 准备空对象 `{}` 作为筛选输入。 | 1. 用户应用会话高级筛选。 | 1. 输入返回错误值 {VALUE_REQUIRED}。<br>2. 输入校验失败后不生成或发送筛选请求。 | P0 | AI-API用例,AI-UI用例,开发必测,测试必测 | 异常 | 来源 CasePlan：CP-010；来源 Acceptance：AE-010；来源 Rule：CW-R008；来源coverage：COV-EX-0014 |
