# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | SL-R001 | linkage | testable | generate_acceptance_example | confirmed | giftCardBulkCreate 复用已有标签时，只能把新礼品卡追加到标签关系，不得移除该标签与历史礼品卡之间的关联。 | 可通过连续两批创建前后的标签成员集合直接验证追加而非替换。 |
| TG-002 | SL-R002 | linkage | testable | generate_acceptance_example | confirmed | 输入新标签时，先创建标签，再把当前批次礼品卡关联到该标签。 | 新标签存在性及其当前批次成员关系均可查询验证。 |
| TG-003 | SL-R003 | linkage | testable | generate_acceptance_example | confirmed | 连续批次使用相同、部分重叠或完全不同的标签集合后，每个标签都应保留其全部正确礼品卡成员。 | 三类标签集合可分别执行并逐标签核对最终成员集合。 |
| TG-004 | SL-R004 | linkage | testable | generate_acceptance_example | confirmed | 新批次每张礼品卡只获得本次输入指定的标签；新旧标签混合输入时，已有关系保留且新关系正确建立。 | 可核对当前批次每张礼品卡的标签集合和已有标签历史成员。 |
| TG-005 | SL-R005 | product_behavior | testable | generate_acceptance_example | confirmed | 批量创建返回 count 与实际新建数量一致，errors 为空时才视为成功，礼品卡标签结果保持既有接口契约。 | GraphQL 响应字段与数据库实际新建记录均可核对。 |
| TG-006 | SL-R006 | risk_hardening | needs_confirmation | needs_confirmation | confirmed | 关系更新应支持批量数量，不引入与历史礼品卡数量线性失控的额外查询；具体性能阈值待确认。 | 可以观测查询数量和耗时，但缺少最大 count、标签数、查询次数及耗时阈值，不能生成确定性验收断言。 |
| TG-007 | SL-R007 | product_behavior | testable | generate_acceptance_example | confirmed | 无权限、非法输入、giftCardCreate 与 giftCardUpdate 的既有行为不得因本次修复改变。 | 权限、非法输入及两个非批量 mutation 均可独立执行回归。 |
| TG-008 | SL-FR001 | linkage | testable | skip_case | confirmed | 不得用当前批次替换已有标签的完整礼品卡成员集合。 | 与 SL-R001 的追加而非替换规则重复。 |
| TG-009 | SL-FR002 | linkage | testable | skip_case | confirmed | 新标签仅建立本次批次所需关系。 | 与 SL-R002、SL-R004 的新标签关系规则重复。 |
| TG-010 | SL-FR004 | linkage | testable | skip_case | confirmed | 第二批复用第一批标签后，第一批礼品卡仍保留该标签。 | 与 SL-R001、SL-R003 的跨批次关系保留规则重复。 |
| TG-011 | SL-FR005 | product_behavior | testable | skip_case | confirmed | count 与实际新建数量一致且 errors 为空时才视为成功。 | 与 SL-R005 的返回成功判定重复。 |
| TG-012 | SL-FR006 | product_behavior | testable | skip_case | confirmed | giftCardCreate、giftCardUpdate 以及既有错误行为不变。 | 与 SL-R007 的兼容性回归规则重复。 |
| TG-013 | SL-FIELD-001 | linkage | testable | skip_case | confirmed | 已有标签采用关系追加，新标签创建后关联当前批次，当前批次礼品卡只获得输入指定标签。 | 与 SL-R001、SL-R002、SL-R004 的关系规则重复。 |
| TG-014 | SL-FIELD-002 | field_constraint | testable | skip_case | confirmed | 返回 count 与实际新建礼品卡数量一致。 | 与 SL-R005 的返回数量规则重复。 |
| TG-015 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 关系替换与追加在单批次中可能都表现正常，必须跨批次检查历史关系。 | 风险本身作为审计记录，跨批次正式行为已由 SL-R001 与 SL-R003 承接。 |
| TG-016 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 大批量礼品卡和高复用标签可能引入查询次数或关系写入性能风险。 | 缺少可判定性能阈值，仅保留非功能风险。 |
| TG-017 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 并发批量创建复用同一标签时的锁、唯一性和最终成员集合未明确。 | 并发一致性契约尚未确认，不生成强业务断言。 |
| TG-018 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | 修复是前向修复，历史已丢失关系不可从数据库自动推导。 | 历史数据恢复不在范围，仅记录前向修复边界。 |
| TG-019 | SL-R008 | field_constraint | testable | generate_acceptance_example | confirmed | giftCardBulkCreate 的标签名称按小写归一并去重，大小写变体或重复输入不得创建重复标签记录或重复关系。 | 可分别核对已有标签大小写变体、新标签重复输入和关系记录数量，三个原子断言均有确定数据 oracle。 |
