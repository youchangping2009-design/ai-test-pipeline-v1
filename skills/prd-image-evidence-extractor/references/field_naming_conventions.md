# Field Naming Conventions

用于将图片中的中文字段名稳定映射成 `field_name`。

## 基本规则

- 使用英文 snake_case
- 优先保留业务语义，不要只按字面直译
- 同一业务字段在不同图片中尽量复用同一个命名
- 列表列头与弹窗字段若语义相同，优先复用同一命名

## 常用映射建议

- 名称类
  - `banner名称` -> `banner_name`
  - `瓷片区名称` -> `tile_name`
  - `金刚区名称` -> `icon_name`
  - `弹窗名称` -> `popup_name`
- 图片/样式类
  - `banner图片` -> `banner_image`
  - `瓷片区样式` -> `tile_style`
  - `金刚区样式` -> `icon_style`
  - `弹窗图片` -> `popup_image`
- 规则/枚举类
  - `展示类型` -> `display_type`
  - `触达用户类型` -> `touch_user_type`
  - `跳转类型` -> `jump_type`
  - `状态` -> `status`
- 条件字段
  - `X` -> `display_day_x`
  - `选择活动` -> `selected_activity`
  - `链接` -> `link_url`
  - `展示规则` -> `display_rule`
  - `展示tab` -> `show_tab`
  - `充值金额` -> `recharge_amount_range`
- 元数据类
  - `创建人` -> `creator_name`
  - `创建时间` -> `created_at`
  - `修改时间` -> `updated_at`

## 控件类型建议

- 文本输入框 -> `text_input`
- 数字输入框 -> `number_input`
- 前后值区间输入 -> `number_input_pair`
- 下拉单选 -> `select_single`
- 下拉多选 -> `select_multi`
- 图片上传 -> `upload_image`
- 开关/状态切换 -> `switch`
- 列表展示列 -> `display_text` 或 `table_column`

## 数据类型建议

- 普通文本 -> `string`
- 数字整数 -> `integer`
- 枚举 -> `enum`
- 多选结果 -> `array`
- 图片 -> `image`
- 时间 -> `datetime`
- 区间 -> `range`

## 避免事项

- 不要把不同业务字段都命名成 `name` / `type` / `image`
- 不要使用拼音
- 不要按页面位置命名，例如 `left_input_1`
- 不要同一字段一会儿叫 `jump_type` 一会儿叫 `redirect_type`
