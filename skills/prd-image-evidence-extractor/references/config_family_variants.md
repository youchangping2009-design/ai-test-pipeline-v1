# Config Family Variants

适用场景：
- 小程序广告位管理中的同构后台页面
- 典型页面包括：`banner配置 / 瓷片区配置 / 金刚区配置 / 弹窗配置`

## 共同骨架

这些页面通常共享以下板块：

- `filter_area`
- `list_area`
- `action_area`
- `edit_modal`
- `sort_modal`
- `field_rule_table`
- `system note / sticky note`

说明：
- `field_rule_table` 默认是字段说明区，不等于新的配置对象
- 若说明表描述的是表单字段效果，应在结构化阶段回挂到所属字段 feature，而不是额外拆一层独立 feature

共同字段家族通常包括：

- 名称
- 样式/图片
- 展示类型
- X
- 触达用户类型
- 跳转类型
- 选择活动
- 链接
- 展示tab
- 状态

共同规则通常包括：

- 后台数据按创建时间倒序
- 单 tab 条数上限
- 排序只展示开启导航
- 初始排序按创建时间
- 删除/关闭后顺位上移
- 已排序后新增置前
- 触达用户类型说明表

## 共同字段包

优先按以下 canonical 字段复用，再映射到各 family 展示名：

- `asset_name`
- `asset_image`
- `display_type`
- `display_after_days`
- `touch_user_type`
- `jump_type`
- `activity_id`
- `link_url`
- `display_tab`
- `status`

family 映射：
- `banner`：`asset_name -> banner名称`，`asset_image -> banner图片`
- `瓷片区`：`asset_name -> 瓷片区名称`，`asset_image -> 瓷片区样式`
- `金刚区`：`asset_name -> 金刚区名称`，`asset_image -> 金刚区样式`
- `弹窗`：`asset_name -> 弹窗名称`，`asset_image -> 弹窗图片`，额外增加 `display_rule`

## 共同用例包

优先复用以下 testcase 骨架：

- 筛选区：名称 / 跳转类型 / 状态筛选
- 添加/编辑弹窗：字段矩阵完整性
- 添加/编辑弹窗：条件联动
- 列表区 + 操作区：列头、预览、编辑/复用/删除/排序入口
- 排序弹窗：初始顺序、删除/关闭后顺位上移、新增置前
- 条数上限：上限内成功、超上限失败
- 触达用户类型：枚举效果 / 附加字段 / 人群分支规则

其中：
- `触达用户类型` 默认挂在所属弹窗或字段联动用例下
- 只有说明表本身存在独立展示要求时，才单独生成“说明表展示”类用例

## 差异点

### banner配置
- 主字段：`banner_name / banner_image`
- 条数上限：5
- 列表列头使用 `banner`

### 瓷片区配置
- 主字段：`tile_name / tile_style`
- 条数上限：4
- 列表列头使用 `瓷片区`

### 金刚区配置
- 主字段：`icon_name / icon_style`
- 条数上限：4
- 跳转类型增加 `展示企微单人单码`
- 触达用户类型说明表增加 `付费未添加企微用户`
- 列表列头使用 `金刚区`

### 弹窗配置
- 主字段：`popup_name / popup_image`
- 条数上限：3
- 列表列头使用 `弹窗`
- 新增字段：`display_rule`
- 跳转类型可包含 `展示企微单人单码`
- 触达用户类型说明表可包含 `付费未添加企微用户`

## 抽取策略

1. 先识别当前页面属于哪个家族成员
2. 复用共同骨架
3. 再抽当前页面的差异字段和差异规则
4. 对条数上限、字段名、样式/图片字段名、触达用户类型行差异做专项校验

## 校验重点

- 是否错误沿用了其他家族成员的字段名
- 是否错误沿用了其他家族成员的条数上限
- 是否遗漏了当前家族成员独有的跳转类型或说明表枚举行
- 是否列表列头和弹窗字段名保持一致

## 家族专属必查项

### banner配置
- `jump_type` 不应包含 `展示企微单人单码`
- 条数上限应为 5

### 瓷片区配置
- 主字段应为 `tile_name / tile_style`
- 条数上限应为 4

### 金刚区配置
- 主字段应为 `icon_name / icon_style`
- `jump_type` 必须包含 `展示企微单人单码`
- `touch_user_type` 说明表必须包含 `付费未添加企微用户`
- 条数上限应为 4

### 弹窗配置
- 主字段应为 `popup_name / popup_image`
- 条数上限应为 3
- 若图中出现 `展示规则`，应抽取为独立字段
