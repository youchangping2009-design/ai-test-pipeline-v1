# Acceptance Examples

| example_id | source_gate_ids | title | given | when | then | verification_side | oracle_strength | confidence | inference_basis |
|---|---|---|---|---|---|---|---|---|---|
| AE-001 | TG-001 | 数字自定义属性的筛选值保持 number 类型 | 会话存在 number 类型自定义属性，用户在[会话列表页]的高级筛选中选择该属性。 | 用户输入数字并应用筛选。 | 筛选控件产生 number 类型的值。<br>筛选请求和客户端匹配使用的值均保持 number 类型。 | 前端与请求层 | business_behavior | confirmed |  |
| AE-002 | TG-002 | 筛选请求保留 0 和 false 并排除真正空值 | 分别准备筛选值 0、false、null、undefined 和空字符串。 | 前端生成会话筛选请求。 | 数值 0 和布尔值 false 均保留在请求值中。<br>null、undefined 和空字符串按空值处理，不作为有效筛选值发送。 | 前端请求层 | business_behavior | confirmed |  |
| AE-003 | TG-003 | 会话属性缺失与显式 0、false 分开匹配 | 会话集合分别包含属性缺失、属性值为数值 0、属性值为布尔值 false 的记录。 | 客户端读取自定义属性并执行筛选匹配。 | 属性缺失的会话不会被当作值为 0 或 false。<br>属性值为 0 或 false 的会话仍可按各自显式值参与匹配。 | 前端列表层 | business_behavior | confirmed |  |
| AE-004 | TG-004 | 客户端二次匹配同时比较值与类型 | 会话属性包含数值 0 和字符串 `0` 等值相同但类型不同的数据。 | 客户端使用数值 0 执行二次筛选匹配。 | 仅数值与类型都相等的会话被视为匹配。<br>字符串 `0` 不会因统一字符串化而与数值 0 匹配。 | 前端列表层 | business_behavior | confirmed |  |
| AE-005 | TG-005 | equal_to 与 not_equal_to 按严格相等结果筛选 | 会话集合同时包含与筛选值类型和值都相等、仅文本表示相同但类型不同的属性值。 | 用户分别使用 equal_to 和 not_equal_to 应用同一筛选值。 | equal_to 只命中类型和值都相等的会话。<br>not_equal_to 排除类型和值都相等的会话，并保留不严格相等的会话。 | 前端列表层 | business_behavior | confirmed |  |
| AE-007 | TG-007 | 既有文本、日期和列表筛选保持原有行为 | 已准备可被文本、日期和列表类型筛选命中的既有会话数据。 | 用户分别应用文本、日期和列表类型的高级筛选。 | 三类筛选均按各自既有值类型和运算规则返回正确会话。<br>本次 number 类型修复不会改变这些筛选类型的结果。 | 前端与请求层 | business_behavior | confirmed |  |
| AE-008 | TG-019 | 空数组筛选值在请求前返回必填错误 | 准备空数组 `[]` 作为筛选输入。 | 用户应用会话高级筛选。 | 输入返回错误值 {VALUE_REQUIRED}。<br>输入校验失败后不生成或发送筛选请求。 | 前端输入与请求层 | hard_block | confirmed |  |
| AE-009 | TG-020 | 早于当前日期天数输入 0 时仍执行范围校验 | “创建时间”筛选条件选择“早于当前日期天数”，输入值为 {0}。 | 用户应用会话高级筛选。 | 系统返回错误值 {VALUE_MUST_BE_BETWEEN_1_AND_998}。<br>数值 {0} 不会因空值保留逻辑而绕过日期范围校验。 | 前端输入校验层 | hard_block | confirmed |  |
| AE-010 | TG-019 | 空对象筛选值在请求前返回必填错误 | 准备空对象 `{}` 作为筛选输入。 | 用户应用会话高级筛选。 | 输入返回错误值 {VALUE_REQUIRED}。<br>输入校验失败后不生成或发送筛选请求。 | 前端输入与请求层 | hard_block | confirmed |  |
