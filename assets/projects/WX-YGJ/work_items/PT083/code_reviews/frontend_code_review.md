# Code Review

- stage: `frontend_code_review`
- review_type: `frontend_code`
- manual_confirmation_required: `true`
- review_policy: `不得修改业务代码，不得修改历史产出物`
- branch: `feature/PT083云挂机用户体验及SDK迭代/260421/sqt`、`feature/PT083云挂机用户体验及SDK迭代/260422/sqt`
- reviewed_at: `2026-04-28`
- latest_testcase_gap_recheck: `2026-04-28`
- recheck_note: `PT083 已重新生成用例，本文件旧用例编号已由 code_reviews/testcase_gap_check.md 与 design/design_feedback.json 中的新编号映射接续。`

## Review Scope

- 对照对象：结构化 PRD / testcase / 当前阶段代码实现
- 前端项目：
  - `/Users/xin/WebstormProjects/platform-cloud-admin-front`
  - `/Users/xin/WebstormProjects/platform-box-h5-ios`
- 代码状态：PT083 前端分支已合入 `origin/dev`，本次通过 merge commit 和 `origin/dev` 快照审查；未切换本地分支。
- 证据快照：
  - `/tmp/pt083-platform-cloud-admin-front`
  - `/tmp/pt083-platform-box-h5-ios`
- 输出目标：识别代码缺口、用例缺口、无效用例、仅 PRD 存在但代码未落地项
- 本阶段不得修改业务代码，不得修改历史产出物

## Findings

| 序号 | 类型 | 描述 | 严重级别 | 证据 |
|------|------|------|----------|------|
| 1 | 代码错漏 | “编辑宣传内容”表单只限制最多 2 组、单组云机类型必填，没有在点击确认时校验“所有云机类型是否都有配置内容”与“是否不存在云机类型相同的配置内容”；仅配 1 组或两组重复类型时前端仍会提交，未按需求 toast “所有云机类型都需要配置宣传内容，且云机类型不重复！”。 | P1 | `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:431`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:437`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:444`; `/tmp/pt083-platform-cloud-admin-front/src/pages/goods/config/index.tsx:448` |
| 2 | 代码错漏 | C 端普通区标题仍展示为“超值套餐”，未按 PRD 更名为“限时购买”。 | P1 | `/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:94`; `/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:102`; `structured_prd.md:102` |
| 3 | 已降级-合理实现 | C 端特价专区直接遍历 `specialGoods` 全量数据，本身没有前端兜底裁剪4个；补充 `platform-cloud-admin` 后确认写侧在特殊区生效商品已有4个时阻止保存，因此正常业务路径下不会返回超过4个特殊区商品，不再作为前端缺陷。 | - | `/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:60`; `/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:62`; `/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudMobileGoodsServiceImpl.java:462` |

## Reclassified Items

- 后台库存预警值：需求口径为正整数且数值下限 200，前端 `min=200` 符合预期，不作为缺陷。
- 宣传图片格式/大小：需求口径为问号提示语，不要求代码层硬限制；前端已有提示“图片支持 gif/jpg/jpeg/png，单张不超过 500k，建议尺寸 1008*160”，不作为缺陷。
- iOS C 端购买页 `phoneType: 1` 和“全新版”背景：iOS 只有全新版，符合预期，不作为缺陷。

## Coverage Mapping

- 已映证：后台云手机商品管理页新增商品区、服务时长 n天x时、宣传内容配置入口；C 端接入 `/order/goodsList/ext` 并拆分 `specialGoods/normalGoods`；0 元商品点击后走 `/order/trialOrder`。
- 已补充映证：后台特殊区超过 4 个的保存拦截由 `platform-cloud-admin` 写侧兜底；编辑宣传内容保存接口服务端已校验云机类型齐全且不重复。
- 未充分映证：库存预警 20 分钟任务和机器人报警属于服务端/定时任务链路。
- 需要联调验证：后台 `savePromoConfig` 的服务端校验提示、图片上传服务端格式/大小拦截、C 端 free trial 成功后是否实际获得云机。

## Invalid Or Stale Cases

- 当前前端目录无法证明 SDK 实际画面尺寸 `720*1280`，且该项已按本轮要求忽略代码错漏。
- 当前前端目录无法证明库存预警任务“每20分钟校验库存并报警”的后端执行效果。
- 当前 `platform-box-h5-ios` 属于 iOS H5，iOS 只有全新版；常规版 tab 不作为该仓库缺陷。

## Missing Testcase Items

| 序号 | 缺漏项 | 补充状态 |
|------|--------|----------|
| 1 | C端0元商品点击后应走免费体验领取链路，不进入支付页 | 已补充 `WX-YGJ-CLOUDTRY-ORDER-MINIAPP-FL-002` |
| 2 | 普通区标题更名为限时购买 | 已有 `WX-YGJ-CLOUDBUY-NORMAL-MINIAPP-FN-002` 覆盖 |
| 3 | 常规版/全新版tab均展示宣传图和改版专区 | 已有 `WX-YGJ-CLOUDBUY-TAB-MINIAPP-FN-001`、`WX-YGJ-CLOUDBUY-CFGSYNC-MINIAPP-FL-001` 覆盖 |
| 4 | 宣传内容云机类型必须齐全且不重复 | 已有 `WX-YGJ-CLOUDADMIN-PROMO-ADMIN-AB-002` 覆盖 |
| 5 | 宣传图片格式、大小、数量和删除重传 | 已有 `WX-YGJ-CLOUDADMIN-PROMO-ADMIN-BD-002`、`WX-YGJ-CLOUDADMIN-PROMO-ADMIN-FN-001` 覆盖 |

## Regenerated Testcase Gap Recheck

本轮重新引入前端分支后，使用 `origin/dev` 读取当前实现，并用两个 PT083 前端目标分支引用确认范围。由于 PT083 前端分支已合入 `origin/dev`，`origin/dev...origin/<target>` diffstat 为空。

| 结论 | 关联设计/用例 | 当前判断 |
|------|---------------|----------|
| 普通区标题更名为限时购买 | `CP-005` / `WX-YGJ-PT083-NORMAL-MINIAPP-FN-001` | 用例已覆盖，但 H5 当前实现仍显示“超值套餐”；这是实现缺口，不是用例缺口，已写入 `DF-004`。 |
| 宣传内容云机类型完整且不重复 | `CP-010` / `WX-YGJ-PT083-PROMO-CLOUDTYPE-ADMIN-AB-001` | 用例已覆盖；前端提交前缺少统一 toast，服务端有兜底校验，已写入 `DF-005`。 |
| 0元商品免费体验链路 | `CP-013` / `WX-YGJ-PT083-FREE-TRIAL-MINIAPP-FL-001` | C端点击0元商品会调用 `/order/trialOrder`，当前用例覆盖主链路；时长/补偿风险转后端设计反馈。 |

本节只记录设计层反馈，不直接修改正式用例。

## Manual Confirmation

- 需要人工确认后才能作为正式 CR 结论进入流水线
- 人工确认完成后，请同步填写对应 confirmation JSON
