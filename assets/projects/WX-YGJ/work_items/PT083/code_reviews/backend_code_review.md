# Code Review

- stage: `backend_code_review`
- review_type: `backend_code`
- manual_confirmation_required: `true`
- review_policy: `不得修改业务代码，不得修改历史产出物`
- branch: `feature/pt083_cloud`
- reviewed_at: `2026-04-28`
- latest_testcase_gap_recheck: `2026-04-28`
- recheck_note: `PT083 已重新生成用例，本文件旧用例编号已由 code_reviews/testcase_gap_check.md 与 design/design_feedback.json 中的新编号映射接续；sceneType=4 重复分配旧风险当前分支已关闭。`

## Review Scope

- 对照对象：结构化 PRD / testcase / 当前阶段服务端代码实现
- 服务端项目：
  - `/Users/xin/IdeaProjects/platform-cloud`
  - `/Users/xin/IdeaProjects/platform-cloud-order`
  - `/Users/xin/IdeaProjects/wx-order-center`
  - `/Users/xin/IdeaProjects/platform-box-order-center`
  - `/Users/xin/IdeaProjects/bt-order-center`
  - `/Users/xin/IdeaProjects/platform-cloud-admin`
- 新增补充快照：
  - `/tmp/pt083-platform-cloud-admin`
- 输出目标：识别代码缺口、用例缺口、无效用例、仅 PRD 存在但代码未落地项
- 本阶段不得修改业务代码，不得修改历史产出物

## Findings

| 序号 | 类型 | 描述 | 严重级别 | 证据 |
|------|------|------|----------|------|
| 1 | 代码错漏 | `platform-cloud` 的 `cloudTryOperate` 对 `sceneType=4` 先确认库存并分配一次云机，但没有 `return`，随后继续执行旧试用逻辑，再扣 Redis 库存、再次分配、再扣 DB 库存；二次验证 `sceneType!=4` 只走旧逻辑一次，不存在同类重复分配，因此这是本次 `sceneType=4` 新增路径问题，不记录为历史实现。 | P0 | `/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:1319`; `/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:1349`; `/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:1378` |
| 2 | 代码错漏 | 订单中心试用时长只使用 `goodsVo.getHour() * 60`。二次验证存储模型中 `duration` 与 `hour` 是两个独立字段，`duration` 表示天、`hour` 表示小时，因此 `n天x时` 会漏算天数，且 `hour == null` 时存在 NPE 风险，确认为真实问题。 | P0 | `/tmp/pt083-wx-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:430`; `/tmp/pt083-bt-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:466`; `/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:465`; `/tmp/pt083-platform-cloud-order/src/main/java/com/wxbz/platform/core/order/entity/CloudMobileGoods.java:47` |
| 3 | 历史实现风险 | 订单中心在远端锁库存后先写 `order_success`，再发 MQ；若 MQ 后续消费或云机分配失败，用户会被重复试用校验拦截但没有拿到云机。二次验证历史付费订单回调也是先保存成功订单再发云机支付 MQ，因此该项记录为已知历史实现模式，但免费体验链路仍需要补偿/重试用例覆盖。 | P1 | `/tmp/pt083-wx-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:420`; `/tmp/pt083-wx-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:431`; `/tmp/pt083-wx-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:286`; `/tmp/pt083-bt-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:287`; `/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:295` |
| 4 | 历史实现风险 | `confirmCloudStock` 先写 Redis 幂等键，再查锁记录；如果首次确认在写入幂等键后失败，短期重试会被拦截。二次验证历史 `lockStock` 也存在先写幂等键再查订单/锁记录的实现模式，因此记录为已知历史实现风险。 | P2 | `/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:2493`; `/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:666` |
| 5 | 已降级-合理实现 | `goodsListExt` 读侧未再裁剪特殊区最多4个，但补充 `platform-cloud-admin` 后确认写侧在新增/编辑生效特殊区商品时按同商品类型统计，已有4个开启状态特殊区商品时阻止保存，因此 C 端最多4个可由写侧强约束保证，不再作为代码错漏项。 | - | `/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudMobileGoodsServiceImpl.java:454`; `/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudMobileGoodsServiceImpl.java:462` |
| 6 | 已忽略-前端限制 | `goodsRegion` 写侧未额外限制非法枚举值，但后台前端商品区字段为必填枚举，候选仅 `1=普通区`、`2=特殊区`，正常业务路径不能提交非法值；按本轮口径不作为代码错漏。 | - | `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:47`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:214`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:216`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:217` |

## Regenerated Testcase Gap Recheck

本轮重新引入前后端分支后，使用 `origin/dev` 读取当前实现，并用 `origin/feature/pt083_cloud` 引用确认分支范围。由于 PT083 分支已合入 `origin/dev`，`origin/dev...origin/feature/pt083_cloud` diffstat 为空。

| 结论 | 关联设计/用例 | 当前判断 |
|------|---------------|----------|
| 免费体验时长换算缺少用例 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 当前正式用例只覆盖领取成功，未覆盖 `duration + hour` 换算；已写入 `DF-001`。 |
| 免费体验成功订单到 MQ 分配缺少失败补偿验证 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 需要补 risk/API 计划，不应混入主验收用例；已写入 `DF-002`。 |
| 库存确认幂等键先写入风险 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 作为 risk_note 保留；已写入 `DF-003`。 |
| `sceneType=4` 重复分配旧风险 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | 当前代码在新分支成功后已有 `return`，旧 P0 不再成立；已写入 `DF-006`。 |

本节只记录设计层反馈，不直接修改正式用例。

## Ignored Items

- `720*1280` 实际画面尺寸：按本轮要求忽略，不作为服务端或前端代码错漏项；该能力由三方云机/SDK能力控制，不再要求代码侧补充验证。

## Coverage Mapping

- 已映证：订单中心新增 `/order/goodsList/ext` 和 `/order/trialOrder`，云平台新增 `/user/facilities/stock/lock`，`platform-cloud-order` 提供 `/goods/listExt`，`platform-cloud-admin` 承载 `admin/cloudMobileGoods/*` 后台写侧接口。
- 已补充映证：后台新增/编辑商品、编辑宣传内容、特殊区数量保存拦截、商品类型排序、用户标签和报警通知人数据源接口。
- 未充分映证：20 分钟库存预警任务和机器人报警执行链路、宣传图片上传服务实际格式/大小拦截。
- 需要前端 CR 映证：购买页双 tab 展示、宣传图/宣传专区样式、首屏 2.5 卡片、限时购买首屏 2 个以上、商品选中态、数量与合计金额联动。

## Invalid Or Stale Cases

- 当前服务端目录无法证明以下 UI 型用例：tab 展示、图片尺寸视觉投放、C 端换行、首屏 2.5 卡片、底部结算区交互。
- 当前服务端目录无法证明后台管理页 UI 型用例：按钮更名、弹窗字段展示、删除后重新上传、添加按钮禁用态。
- 原 P3 “筛选区过滤能力可能超出本次变更范围”已按产品范围移除/不纳入本期影响评估。

## Testcase Supplement Status

| 序号 | 原缺漏项 | 补充状态 |
|------|----------|----------|
| 1 | 免费体验接口成功链路 | 已补充 `WX-YGJ-CLOUDTRY-ORDER-API-FL-001` |
| 2 | 免费体验时长计算 | 已补充 `WX-YGJ-CLOUDTRY-DURATION-API-BD-001` |
| 3 | 免费体验异常链路 | 已补充 `WX-YGJ-CLOUDTRY-ORDER-API-AB-001`、`WX-YGJ-CLOUDTRY-ORDER-API-AB-002` |
| 4 | 重复试用规则 | 已补充 `WX-YGJ-CLOUDTRY-REPEAT-API-AB-001` |
| 5 | 扩展商品列表服务端契约 | 已补充 `WX-YGJ-CLOUDBUY-EXT-API-DV-001`、`WX-YGJ-CLOUDBUY-EXT-API-BD-001`；其中特殊区最多4个改由后台写侧用例 `WX-YGJ-CLOUDADMIN-ADDMODAL-ADMIN-AB-001` 承接 |
| 6 | 库存锁定幂等与解冻 | 已补充 `WX-YGJ-CLOUDTRY-STOCK-API-DV-001` |
| 7 | 720*1280 实际画面尺寸 | 按本轮要求忽略，不补充新增用例 |

## Manual Confirmation

- 需要人工确认后才能作为正式 CR 结论进入流水线
- 人工确认完成后，请同步填写对应 confirmation JSON
- 当前结论为静态代码评审结论；本机未安装 `mvn`，未执行 Java 编译。
