# Testpoints View

- Project: `OSS-BLIND`
- Work Item: `SALEOR-19804`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 复用已有标签时追加新礼品卡并保留历史成员 | 复用已有标签后，其成员集合包含历史礼品卡和当前批次礼品卡，历史关系不被移除。 | P0 | CP-001 | True |
| TP-002 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 新标签创建后关联当前批次礼品卡 | 输入不存在的标签时创建该标签，并将本次成功创建的全部礼品卡关联到该标签。 | P1 | CP-002 | True |
| TP-003 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 四个连续批次后标签成员集合等于批次并集 | 四批输入依次为 G1/G2-{red,blue}、G3/G4-{red,blue}、G5/G6-{blue,green}、G7/G8-{yellow}；最终 red、blue、green、yellow 成员集合分别精确等于 {G1-G4}、{G1-G6}、{G5,G6}、{G7,G8}。 | P0 | CP-003 | True |
| TP-004 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 新旧标签混合输入只建立指定关系 | 当前批次礼品卡只获得输入指定的新旧标签，同时保留已有标签的历史成员关系。 | P0 | CP-004 | True |
| TP-005 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | data_persistence | 成功响应数量与实际新建礼品卡一致 | 响应 `count` 等于实际新建数量，`errors` 为空时才判定成功，标签结果符合既有接口契约。 | P0 | CP-005 | True |
| TP-006 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | permission_scope | 权限、非法输入及非批量礼品卡操作行为不回退 | 无权限与非法输入保持既有错误结果，`giftCardCreate` 和 `giftCardUpdate` 的成功及标签关系行为保持不变。 | P1 | CP-006 | True |
| TP-007 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 已有标签大小写变体复用同一小写记录 | 已有 {vip} 时输入 {VIP} 复用同一标签，数据库仍只有一条名称为 {vip} 的记录。 | P0 | CP-007 | True |
| TP-008 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | data_persistence | 重复输入的新标签只创建一条小写记录 | 同一请求输入 {New,new,NEW} 后，数据库只新增一条名称为 {new} 的标签记录。 | P0 | CP-008 | True |
| TP-009 | giftCardBulkCreate GraphQL 接口 | 批量创建请求 | 礼品卡批量创建 | 批量礼品卡标签关系追加 | cross_surface_linkage | 大小写变体和重复标签只建立一次礼品卡关系 | 大小写变体或重复标签输入只为每张当前批次礼品卡建立一次归一标签关系。 | P0 | CP-009 | True |
