# PT083 Testcase Gap Check From Code Branches

- checked_at: `2026-04-28`
- latest_recheck_at: `2026-04-28`
- project_code: `WX-YGJ`
- work_item_id: `PT083`
- policy: `只做测试用例错漏检查，不修改业务代码，不直接覆盖正式 testcase`
- testcase_truth_source: `testcases/testcases_main.md`

## Branch Scope

| 端 | 仓库 | 分支 | 本地引用 |
|----|------|------|----------|
| 后端 | `/Users/xin/IdeaProjects/platform-cloud` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@78d9f25fdd07592f558bbcf7d3e5d9f174ef4852` |
| 后端 | `/Users/xin/IdeaProjects/platform-cloud-admin` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@a5b6bd3dde07ce2f74238b5f1590e8f7690fd1b7` |
| 后端 | `/Users/xin/IdeaProjects/platform-cloud-order` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@eedafaaa4946cb886dc246c918dbe78a28f84e7a` |
| 后端 | `/Users/xin/IdeaProjects/platform-box-order-center` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@f0cc786ab8777ed99708a7aee00f76c3904aace3` |
| 后端 | `/Users/xin/IdeaProjects/wx-order-center` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@aef5a08d52df93dc509403fc36e82f0a7d502a9f` |
| 后端 | `/Users/xin/IdeaProjects/bt-order-center` | `feature/pt083_cloud` | `origin/feature/pt083_cloud@31376d0fab0ae22acb6fb631eb773083a2438535` |
| 前端 | `/Users/xin/WebstormProjects/platform-cloud-admin-front` | `feature/PT083云挂机用户体验及SDK迭代/260421/sqt` | `origin/feature/PT083云挂机用户体验及SDK迭代/260421/sqt@284a67f5e1669e4c7d6d43c056a5ea7c16c329fa` |
| 前端 | `/Users/xin/WebstormProjects/platform-box-h5-ios` | `feature/PT083云挂机用户体验及SDK迭代/260422/sqt` | `origin/feature/PT083云挂机用户体验及SDK迭代/260422/sqt@9844de57242d7c2c3f5db89ef70ce160f5fd3251` |

这些分支相对 `origin/dev...origin/<target>` 的 diffstat 当前为空，说明 PT083 分支内容已合入 `origin/dev`。本轮使用 `origin/dev` 读取实现细节，并用目标分支引用证明范围。

## Verdict

| 序号 | 结论类型 | 关联 CasePlan / Testcase | 结论 | 处理 |
|------|----------|--------------------------|------|------|
| 1 | 用例缺漏 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 免费体验试用时长只覆盖领取成功，缺少 `duration + hour` 换算校验。代码中 `trialOrder` 仍按 `goodsVo.getHour() * 60` 设置分钟数。 | 写入 `DF-001`，下一轮扩展 case_plan。 |
| 2 | 用例缺漏 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 免费体验链路缺少“订单已成功落库但 MQ/云机分配失败”的补偿/重试验证。 | 写入 `DF-002`，建议进入 risk/API 计划。 |
| 3 | 风险项 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | `confirmCloudStock` 先写幂等键再查锁记录，短期失败重试可能被拦截。 | 写入 `DF-003`，保留为 risk_note。 |
| 4 | 实现缺口 | `CP-005` / `WX-YGJ-PT083-NORMAL-MINIAPP-FN-001` | 用例已要求普通区标题展示为“限时购买”，但 H5 代码仍显示“超值套餐”。 | 写入 `DF-004`，不降低用例断言。 |
| 5 | 实现缺口 | `CP-010` / `WX-YGJ-PT083-PROMO-CLOUDTYPE-ADMIN-AB-001` | 用例已覆盖宣传内容云机类型完整且不重复；前端缺少提交前统一 toast，服务端存在兜底校验但文案与产品指定不完全一致。 | 写入 `DF-005`，执行时观察前后端提示。 |
| 6 | 旧风险关闭 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 旧后端评审中的 `sceneType=4` 重复分配风险当前已不成立，代码在新分支逻辑成功后已有 `return`。 | 写入 `DF-006`，不新增重复分配主用例。 |

## No Case Change Applied

- 未直接修改 `testcases/testcases_main.md`。
- 未切换 testcase 真源。
- 后续如要补用例，应先补 `case_plan.json`，再从 case_plan 派生正式 testcase。

## Latest Fix Recheck

本轮已执行 `git fetch origin` 刷新前后端代码仓远端引用，并复查上述 5 个打开问题。

| 反馈ID | 问题 | 最新代码状态 | 证据 |
|--------|------|--------------|------|
| DF-001 | 免费体验时长只取 hour，未纳入 duration 天数 | 代码侧已修复；测试资产仍建议补时长边界用例 | `platform-box-order-center@origin/dev`、`wx-order-center@origin/dev`、`bt-order-center@origin/dev` 均改为 `duration * 24 * 60 + hour * 60` |
| DF-002 | 成功订单落库后 MQ/云机分配失败缺少补偿验证 | 未见修复 | `orderSuccessService.save(orderSuccess)` 后仍直接 `rocketMqService.cloudTrySend(dto)` |
| DF-003 | `confirmCloudStock` 先写 Redis 幂等键再查锁记录 | 未见修复 | `confirmCloudStock` 仍先 `setIfAbsent`，后查 `CloudStockLock` |
| DF-004 | H5 普通区标题仍显示“超值套餐” | 未见修复 | `platform-box-h5-ios@origin/dev:src/views/cloud/purchase.vue` 仍为“超值套餐” |
| DF-005 | 宣传内容完整且不重复缺少前端提交前统一 toast | 未见修复 | `platform-cloud-admin-front@origin/dev` 仍直接调用 `savePromoConfigApi`，未见提交前完整性/重复校验 |
