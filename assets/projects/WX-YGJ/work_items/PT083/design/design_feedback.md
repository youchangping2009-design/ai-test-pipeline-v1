# Design Feedback

本文件记录重新引入前后端代码分支后的用例错漏检查反馈。反馈只进入设计层，不直接覆盖 `testcases_main.md`。

| feedback_id | 类型 | 关联 CasePlan | 结论 | 状态 |
|-------------|------|---------------|------|------|
| DF-001 | case_gap | CP-013/CP-015 | 免费体验时长计算缺少 duration+hour 换算用例 | applied |
| DF-002 | case_gap | CP-013/CP-016 | 成功订单落库后 MQ/分配失败缺少补偿验证 | applied |
| DF-003 | risk_note | CP-013/CP-017 | 库存确认幂等键先写入存在短期重试风险 | applied |
| DF-004 | implementation_gap | CP-005 | “限时购买”用例已覆盖，前端仍显示“超值套餐” | accepted |
| DF-005 | implementation_gap | CP-010 | 宣传内容完整且不重复用例已覆盖，前端缺少提交前统一 toast | accepted |
| DF-006 | no_action | CP-013 | sceneType=4 重复分配旧风险当前分支已关闭 | accepted |

## Follow-up

- 下一轮若要修补用例，应先扩展 `case_plan.json`，再派生 testcase。
- `risk_note` / `api_guard` 计划不得混入 `product_acceptance` 主用例。
- 不因当前代码缺口降低正式用例断言。

## Latest Fix Recheck

已使用 `git fetch origin` 刷新前后端代码后复查：

- `DF-001` 代码侧已修复：平台/微信/BT 三个 order-center 均已改为按 `duration * 24 * 60 + hour * 60` 计算免费体验分钟数；测试资产已补 `CP-015` 和 `WX-YGJ-PT083-FREE-TRIAL-DURATION-API-BD-001`。
- `DF-002` 未见修复：成功订单落库后仍直接发送 CloudTry MQ，未见失败补偿/回滚链路；测试资产已补 `CP-016` 风险计划，不混入主验收用例。
- `DF-003` 未见修复：`confirmCloudStock` 仍先写 Redis 幂等键，再查询锁定记录；测试资产已补 `CP-017` 风险计划，不混入主验收用例。
- `DF-004` 未见修复：H5 购买页普通区标题仍显示“超值套餐”。
- `DF-005` 未见修复：后台宣传内容提交前仍未见完整性/重复前置校验与统一 toast。
