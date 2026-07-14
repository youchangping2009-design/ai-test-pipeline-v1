# Frontend Backend Mapping Check

- stage: `frontend_backend_mapping`
- project_code: `WX-YGJ`
- work_item_id: `PT083`
- checked_at: `2026-04-28`
- branch_scope:
  - backend: `feature/pt083_cloud`
  - admin_frontend: `feature/PT083云挂机用户体验及SDK迭代/260421/sqt`
  - h5_frontend: `feature/PT083云挂机用户体验及SDK迭代/260422/sqt`

## Scope

- 前端代码：
  - `/Users/xin/WebstormProjects/platform-cloud-admin-front`
  - `/Users/xin/WebstormProjects/platform-box-h5-ios`
- 服务端代码：
  - `/Users/xin/IdeaProjects/platform-cloud`
  - `/Users/xin/IdeaProjects/platform-cloud-order`
  - `/Users/xin/IdeaProjects/wx-order-center`
  - `/Users/xin/IdeaProjects/platform-box-order-center`
  - `/Users/xin/IdeaProjects/bt-order-center`
  - `/Users/xin/IdeaProjects/platform-box-admin`
  - `/Users/xin/IdeaProjects/wx-box-admin`
  - `/Users/xin/IdeaProjects/platform-cloud-admin`
- 代码快照：
  - `/tmp/pt083-platform-cloud-admin-front`
  - `/tmp/pt083-platform-box-h5-ios`
  - `/tmp/pt083-platform-cloud`
  - `/tmp/pt083-platform-cloud-order`
  - `/tmp/pt083-platform-box-order-center`
  - `/tmp/pt083-wx-order-center`
  - `/tmp/pt083-bt-order-center`
  - `/tmp/pt083-platform-cloud-admin`

## Mapping Matrix

| 序号 | 前端入口 | 前端接口 | 服务端映射 | 状态 | 结论 |
|------|----------|----------|------------|------|------|
| 1 | C端购买页商品列表 | `POST /platform-box-order/order/goodsList/ext` | `platform-box-order-center` `/order/goodsList/ext` -> `sdkService.getGoodsListExt` -> `platform-cloud-order` `/goods/listExt` | 已映射 | 链路可达；特殊区最多4个由 `platform-cloud-admin` 写侧保证，商品区正常业务路径由前端必填枚举限制为普通区/特殊区。 |
| 2 | C端0元免费体验 | `POST /platform-box-order/order/trialOrder` | `platform-box-order-center` `/order/trialOrder` -> `OrderServiceImpl.trialOrder` -> `platform-cloud` `/user/facilities/stock/lock` -> MQ -> `CloudTryEventConsumer` -> `cloudTryOperate` | 已映射 | 链路可达；保留服务端已记录的 `sceneType=4` 重复分配、试用时长漏算、先写成功订单再发MQ风险。 |
| 3 | C端正常付费购买 | `POST /platform-cloud-order/order/preCreate` | 历史购买链路，不属于本次新增映射重点 | 已映射-历史 | 本次仅确认0元商品分支不会走预创建订单；付费链路沿用历史实现。 |
| 4 | 后台商品列表 | `admin/cloudMobileGoods/list` | `platform-cloud-admin` `/admin/cloudMobileGoods/list` -> `CloudMobileGoodsService.goodsList` | 已映射 | 列表返回商品区、库存预警值、报警通知人等新增字段，并补齐展示用户标签名称。 |
| 5 | 后台新增/编辑/删除商品 | `admin/cloudMobileGoods/add`、`update`、`delete/{id}` | `platform-cloud-admin` `/admin/cloudMobileGoods/add/update/delete/{id}` -> `CloudMobileGoodsServiceImpl.add/updateConfig/delete` | 已映射 | 服务时长、价格、排序、特殊区最多4个、库存预警下限200有写侧校验；商品区由后台前端必填枚举限制为普通区/特殊区。 |
| 6 | 后台宣传内容读取/保存 | `admin/cloudMobileGoods/promoConfig`、`savePromoConfig` | `platform-cloud-admin` `/admin/cloudMobileGoods/promoConfig/savePromoConfig` -> Redis `CLOUD_PROMO_CONFIG_KEY` -> `platform-cloud-order` `/goods/listExt` 读取 | 已映射 | 服务端保存时校验云机类型不重复且必须覆盖0/1；前端仍缺少产品指定统一 toast。 |
| 7 | 后台商品类型排序 | `admin/cloudMobileGoods/typeSortList`、`typeSortUpdate` | `platform-cloud-admin` `/admin/cloudMobileGoods/typeSortList/typeSortUpdate` -> `CloudGoodsTypeSortServiceImpl` | 已映射 | 排序读写链路可达；前端固定提交常规版/全新版顺序。 |
| 8 | 后台用户标签/管理员列表 | `admin/cloudMobileGoods/boxPersonUseTagList`、`boxAdminList` | `platform-cloud-admin` `/admin/cloudMobileGoods/boxPersonUseTagList/boxAdminList` -> `BoxInfoService` | 已映射 | 展示用户数据源、购买数量报警通知人数据源已映射到盒子服务。 |

## Evidence

- C端扩展商品列表前端调用：`/tmp/pt083-platform-box-h5-ios/src/apis/cloud.js:70`
- C端扩展商品列表入口：`/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:259`
- Order Center 扩展商品列表接口：`/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/controller/OrderController.java:119`
- Order Center 扩展商品列表服务：`/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:375`
- Cloud Order 扩展商品列表接口：`/tmp/pt083-platform-cloud-order/src/main/java/com/wxbz/platform/core/order/controller/CloudMobileGoodsController.java:54`
- Cloud Order 特殊区/普通区分区：`/tmp/pt083-platform-cloud-order/src/main/java/com/wxbz/platform/core/order/service/impl/CloudMobileGoodsServiceImpl.java:95`
- Cloud Admin 商品管理接口：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/controller/CloudMobileGoodsController.java:45`
- Cloud Admin 商品新增/编辑接口：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/controller/CloudMobileGoodsController.java:54`
- Cloud Admin 特殊区最多4个写侧校验：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudMobileGoodsServiceImpl.java:454`
- Cloud Admin 宣传内容保存校验：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudMobileGoodsServiceImpl.java:347`
- Cloud Admin 商品类型排序：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/service/impl/CloudGoodsTypeSortServiceImpl.java:48`
- Cloud Admin 用户标签/报警通知人数据源：`/tmp/pt083-platform-cloud-admin/cloud-admin/src/main/java/com/hzwxbz/cloud/admin/fuc/cloud/controller/CloudMobileGoodsController.java:101`
- C端免费体验前端调用：`/tmp/pt083-platform-box-h5-ios/src/apis/cloud.js:233`
- C端免费体验入口：`/tmp/pt083-platform-box-h5-ios/src/views/cloud/purchase.vue:300`
- Order Center 免费体验接口：`/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/controller/OrderController.java:108`
- Order Center 免费体验服务：`/tmp/pt083-platform-box-order-center/src/main/java/com/wxbz/box/core/order/service/impl/OrderServiceImpl.java:414`
- Cloud 库存锁定接口：`/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/controller/UserFacilitiesController.java:256`
- Cloud 免费体验 MQ 消费：`/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/consumer/CloudTryEventConsumer.java:48`
- Cloud 免费体验分配：`/tmp/pt083-platform-cloud/src/main/java/com/wxbz/platform/core/cloud/service/impl/UserFacilitiesServiceImpl.java:1319`
- 后台商品接口前端定义：`/tmp/pt083-platform-cloud-admin-front/src/api/goods/goodsApi.ts:4`
- 后台商品页调用点：`/tmp/pt083-platform-cloud-admin-front/src/pages/goods/index.tsx:54`

## Mapping Findings

| 序号 | 类型 | 描述 | 严重级别 |
|------|------|------|----------|
| 1 | 映射完成 | 补充 `platform-cloud-admin` 后，后台 `admin/cloudMobileGoods/add/update/delete/list`、`promoConfig/savePromoConfig`、`typeSortUpdate`、`boxPersonUseTagList`、`boxAdminList` 均已找到同路径 controller 和服务实现。 | - |
| 2 | 已忽略-前端限制 | C端 `/order/goodsList/ext` 读侧按 `goodsRegion=2` 拆特殊区，其余归普通区；后台前端商品区字段为必填枚举且候选仅普通区/特殊区，按本轮口径不作为映射风险。 | - |
| 3 | 映射风险 | C端 `/order/trialOrder` 已映射到库存锁定和 MQ 分配链路，但链路中存在 `sceneType=4` 重复分配、时长漏算、先写成功订单后发 MQ 的既有评审问题。 | P0 |

## Next Actions

- 后续修复优先级：优先处理免费体验链路 P0 问题。
- 联调验证重点：后台商品保存 -> `platform-cloud-order` 扩展商品列表 -> C端特价专区/限时购买展示，以及宣传内容 Redis 配置同步。
