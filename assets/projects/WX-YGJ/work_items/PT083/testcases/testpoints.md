# Testpoints View

- Project: `WX-YGJ`
- Work Item: `PT083`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：promotion_slogan; value_constraint | 系统按来源规则判定并明确反馈：promotion_slogan; value_constraint。 | P0 | CP-001 | True |
| TP-002 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：performance_parameters; value_constraint | 系统按来源规则判定并明确反馈：performance_parameters; value_constraint。 | P0 | CP-002 | True |
| TP-003 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | ui_display | 读侧展示：后台未配置特殊区商品时隐藏 | 页面可直接观察到来源规则所述结果：后台未配置特殊区商品时隐藏。 | P1 | CP-003 | True |
| TP-004 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | ui_display | 读侧展示：最多展示4个商品 | 页面可直接观察到来源规则所述结果：最多展示4个商品。 | P1 | CP-004 | True |
| TP-005 | 云挂机购买页 | 版本Tab | 云挂机购买页 | 版本Tab | ui_display | 业务结果：original_price; value_constraint | 最终业务状态与来源规则一致：original_price; value_constraint。 | P1 | CP-005 | True |
| TP-006 | 云挂机购买页 | 普通商品列表 | 云挂机购买页 | 普通商品列表 | ui_display | 业务结果：current_price; value_constraint | 最终业务状态与来源规则一致：current_price; value_constraint。 | P1 | CP-006 | True |
| TP-007 | 云挂机购买页 | 普通商品列表 | 云挂机购买页 | 普通商品列表 | ui_display | 业务结果：service_duration; value_constraint | 最终业务状态与来源规则一致：service_duration; value_constraint。 | P1 | CP-007 | True |
| TP-008 | 云挂机购买页 | 普通商品列表 | 云挂机购买页 | 普通商品列表 | ui_display | 业务结果：in_box_sort_order; value_constraint; integer_only=True | 最终业务状态与来源规则一致：in_box_sort_order; value_constraint; integer_only=True。 | P1 | CP-008 | True |
| TP-009 | 云挂机购买页 | 普通商品列表 | 云挂机购买页 | 普通商品列表 | ui_display | 业务结果：inventory_warning_threshold; value_constraint; integer_only=True | 最终业务状态与来源规则一致：inventory_warning_threshold; value_constraint; integer_only=True。 | P1 | CP-009 | True |
| TP-010 | 云挂机购买页 | 普通商品列表 | 云挂机购买页 | 普通商品列表 | ui_display | 业务结果：purchase_alert_recipient; data_source_constraint; data_source=盒子后台管理员列表 | 最终业务状态与来源规则一致：purchase_alert_recipient; data_source_constraint; data_source=盒子后台管理员列表。 | P1 | CP-010 | True |
| TP-011 | 盒子管理后台-云手机商品管理 | 操作区 | 云手机商品管理 | 操作区 | save_block | 约束判定：天数最大370，小时最大23，所有项不可同时为0，后端以秒为单位 | 系统按来源规则判定并明确反馈：天数最大370，小时最大23，所有项不可同时为0，后端以秒为单位。 | P0 | CP-011 | True |
| TP-012 | 盒子管理后台-云手机商品管理 | 操作区 | 云手机商品管理 | 操作区 | save_block | 约束判定：特殊区商品数量必须小于等于4，超过4个时不可保存 | 系统按来源规则判定并明确反馈：特殊区商品数量必须小于等于4，超过4个时不可保存。 | P0 | CP-012 | True |
| TP-013 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：正整数，上限1000；相同排序值按创建时间倒序排列 | 系统按来源规则判定并明确反馈：正整数，上限1000；相同排序值按创建时间倒序排列。 | P0 | CP-013 | True |
| TP-014 | 盒子管理后台-云手机商品管理-添加 | 商品区与库存规则说明表 | 云手机商品管理 | 商品区与库存规则说明表 | backend_job | 后台任务：正整数，上限200；按固定频率校验库存是否小于等于配置数量 | 任务结果和可观察通知符合来源规则：正整数，上限200；按固定频率校验库存是否小于等于配置数量。 | P0 | CP-014 | True |
| TP-015 | 盒子管理后台-云手机商品管理-添加 | 商品区与库存规则说明表 | 云手机商品管理 | 商品区与库存规则说明表 | cross_surface_linkage | 跨端联动：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知 | B端、服务端与C端的可观察结果保持一致：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知。 | P0 | CP-015 | True |
| TP-016 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：已有功能，数值限制大于0.00 | 系统按来源规则判定并明确反馈：已有功能，数值限制大于0.00。 | P0 | CP-016 | True |
| TP-017 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：已有功能，数值限制大于0.00 | 系统按来源规则判定并明确反馈：已有功能，数值限制大于0.00。 | P0 | CP-017 | True |
| TP-018 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：数字选择器，必填；天最大370、时最大23，所有项不可同时为0，后端以秒为单位 | 系统按来源规则判定并明确反馈：数字选择器，必填；天最大370、时最大23，所有项不可同时为0，后端以秒为单位。 | P0 | CP-018 | True |
| TP-019 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：下拉单选，必填，content：特殊区、普通区；特殊区商品数量小于等于4 | 系统按来源规则判定并明确反馈：下拉单选，必填，content：特殊区、普通区；特殊区商品数量小于等于4。 | P0 | CP-019 | True |
| TP-020 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：数字框，必填，正整数，上限1000；相同值按创建时间倒序 | 系统按来源规则判定并明确反馈：数字框，必填，正整数，上限1000；相同值按创建时间倒序。 | P0 | CP-020 | True |
| TP-021 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：已有功能，增加未配置提示；服务时长结束后C端不再展示 | 页面可直接观察到来源规则所述结果：已有功能，增加未配置提示；服务时长结束后C端不再展示。 | P1 | CP-021 | True |
| TP-022 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：数字框，非必填，正整数，上限200；按固定频率校验库存 | 系统按来源规则判定并明确反馈：数字框，非必填，正整数，上限200；按固定频率校验库存。 | P0 | CP-022 | True |
| TP-023 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：下拉单选，必填，content：盒子后台管理员列表 | 系统按来源规则判定并明确反馈：下拉单选，必填，content：盒子后台管理员列表。 | P0 | CP-023 | True |
| TP-024 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | backend_job | 后台任务：云手机相关报警 | 任务结果和可观察通知符合来源规则：云手机相关报警。 | P0 | CP-024 | True |
| TP-025 | 盒子管理后台-云手机商品管理 | 商品列表 | 云手机商品管理 | 商品列表 | ui_display | 读侧展示：【云挂机库存不足通知】 | 页面可直接观察到来源规则所述结果：【云挂机库存不足通知】。 | P1 | CP-025 | True |
| TP-026 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：玩心盒子后台_云挂机_云手机商品管理 | 页面可直接观察到来源规则所述结果：玩心盒子后台_云挂机_云手机商品管理。 | P1 | CP-026 | True |
| TP-027 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | cross_surface_linkage | 跨端联动：配置ID、商品名称、云机类型、云机服务时长、通知时间、通知人由配置或系统生成 | B端、服务端与C端的可观察结果保持一致：配置ID、商品名称、云机类型、云机服务时长、通知时间、通知人由配置或系统生成。 | P0 | CP-027 | True |
| TP-028 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 业务结果：cloud_machine_type; data_source_constraint; data_source=盒子现有云机类型 | 最终业务状态与来源规则一致：cloud_machine_type; data_source_constraint; data_source=盒子现有云机类型。 | P1 | CP-028 | True |
| TP-029 | 云挂机购买页 | 宣传图占位 | 云挂机购买页 | 宣传图占位 | ui_display | 业务结果：promotion_image; value_constraint | 最终业务状态与来源规则一致：promotion_image; value_constraint。 | P1 | CP-029 | True |
| TP-030 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 业务结果：promotion_slogan; value_constraint | 最终业务状态与来源规则一致：promotion_slogan; value_constraint。 | P1 | CP-030 | True |
| TP-031 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | field_rule | 业务结果：performance_parameters; value_constraint | 最终业务状态与来源规则一致：performance_parameters; value_constraint。 | P1 | CP-031 | True |
| TP-032 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | save_block | 约束判定：保存前校验所有云机类型均已配置且不存在重复 | 系统按来源规则判定并明确反馈：保存前校验所有云机类型均已配置且不存在重复。 | P0 | CP-032 | True |
| TP-033 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | prompt_display | 提示展示：最多上传5张，支持gif/jpg/jpeg/png，单张最大500K，建议尺寸1008*160 | 页面展示来源中的建议或提示文案：最多上传5张，支持gif/jpg/jpeg/png，单张最大500K，建议尺寸1008*160；建议内容不作为提交结果判定。 | P2 | CP-033 | True |
| TP-034 | 云挂机购买页 | 宣传区 | 云挂机购买页 | 宣传区 | save_block | 约束判定：文本长度20个字符；C端超过一行换行展示 | 系统按来源规则判定并明确反馈：文本长度20个字符；C端超过一行换行展示。 | P0 | CP-034 | True |
| TP-035 | 云挂机购买页 | 宣传区 | 云挂机购买页 | 宣传区 | save_block | 约束判定：文本长度20个字符；C端超过一行换行展示 | 系统按来源规则判定并明确反馈：文本长度20个字符；C端超过一行换行展示。 | P0 | CP-035 | True |
| TP-036 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | save_block | 约束判定：下拉列表框，必填，默认为空，可编辑；单选，content为盒子现有云机类型 | 系统按来源规则判定并明确反馈：下拉列表框，必填，默认为空，可编辑；单选，content为盒子现有云机类型。 | P0 | CP-036 | True |
| TP-037 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | prompt_display | 提示展示：图片按钮，必传，最多5张；支持gif/jpg/jpeg/png，最大500K，建议尺寸1008*160；支持拖拽和删除 | 页面展示来源中的建议或提示文案：图片按钮，必传，最多5张；支持gif/jpg/jpeg/png，最大500K，建议尺寸1008*160；支持拖拽和删除；建议内容不作为提交结果判定。 | P2 | CP-037 | True |
| TP-038 | 云挂机购买页 | 宣传区 | 云挂机购买页 | 宣传区 | save_block | 约束判定：文本框，必填，20个字符；C端超过一行换行展示 | 系统按来源规则判定并明确反馈：文本框，必填，20个字符；C端超过一行换行展示。 | P0 | CP-038 | True |
| TP-039 | 云挂机购买页 | 宣传区 | 云挂机购买页 | 宣传区 | save_block | 约束判定：文本框，必填，20个字符；C端超过一行换行展示 | 系统按来源规则判定并明确反馈：文本框，必填，20个字符；C端超过一行换行展示。 | P0 | CP-039 | True |
| TP-040 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：点击增加一条宣传配置，最多额外新增1块；达到2条时禁用按钮 | 系统按来源规则判定并明确反馈：点击增加一条宣传配置，最多额外新增1块；达到2条时禁用按钮。 | P1 | CP-040 | True |
| TP-041 | 云挂机购买页 | 版本Tab | 云挂机购买页 | 版本Tab | field_rule | 业务结果：全新版和常规版两个Tab均可见、可切换并展示对应内容 | 最终业务状态与来源规则一致：全新版和常规版两个Tab均可见、可切换并展示对应内容。 | P1 | CP-041 | True |
| TP-042 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | field_rule | 业务结果：后台未配置特殊区商品时，C端隐藏整个特价专区 | 最终业务状态与来源规则一致：后台未配置特殊区商品时，C端隐藏整个特价专区。 | P1 | CP-042 | True |
| TP-043 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | field_rule | 业务结果：库存不足时同步隐藏商品、停止分配云机并发送告警 | 最终业务状态与来源规则一致：库存不足时同步隐藏商品、停止分配云机并发送告警。 | P1 | CP-043 | True |
| TP-044 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：所有云机类型均需配置宣传内容且云机类型不可重复 | 最终业务状态与来源规则一致：所有云机类型均需配置宣传内容且云机类型不可重复。 | P1 | CP-044 | True |
| TP-045 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：promotion_slogan; value_constraint（场景2） | 系统按来源规则判定并明确反馈：promotion_slogan; value_constraint。 | P1 | CP-045 | True |
| TP-046 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | save_block | 约束判定：performance_parameters; value_constraint（场景3） | 系统按来源规则判定并明确反馈：performance_parameters; value_constraint。 | P1 | CP-046 | True |
| TP-047 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | save_block | 约束判定：后台未配置特殊区商品时隐藏（场景4） | 系统按来源规则判定并明确反馈：后台未配置特殊区商品时隐藏。 | P1 | CP-047 | True |
| TP-048 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 读侧展示：promotion_slogan; value_constraint（场景2） | 页面可直接观察到来源规则所述结果：promotion_slogan; value_constraint。 | P1 | CP-048 | True |
| TP-049 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 读侧展示：performance_parameters; value_constraint（场景3） | 页面可直接观察到来源规则所述结果：performance_parameters; value_constraint。 | P1 | CP-049 | True |
| TP-050 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 读侧展示：后台未配置特殊区商品时隐藏（场景4） | 页面可直接观察到来源规则所述结果：后台未配置特殊区商品时隐藏。 | P1 | CP-050 | True |
| TP-051 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | ui_display | 读侧展示：最多展示4个商品（场景5） | 页面可直接观察到来源规则所述结果：最多展示4个商品。 | P1 | CP-051 | True |
| TP-052 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 读侧展示：天数最大370，小时最大23，所有项不可同时为0，后端以秒为单位（场景6） | 页面可直接观察到来源规则所述结果：天数最大370，小时最大23，所有项不可同时为0，后端以秒为单位。 | P1 | CP-052 | True |
| TP-053 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | ui_display | 读侧展示：特殊区商品数量必须小于等于4，超过4个时不可保存（场景7） | 页面可直接观察到来源规则所述结果：特殊区商品数量必须小于等于4，超过4个时不可保存。 | P1 | CP-053 | True |
| TP-054 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：正整数，上限1000；相同排序值按创建时间倒序排列（场景8） | 页面可直接观察到来源规则所述结果：正整数，上限1000；相同排序值按创建时间倒序排列。 | P1 | CP-054 | True |
| TP-055 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：已有功能，数值限制大于0.00（场景9） | 页面可直接观察到来源规则所述结果：已有功能，数值限制大于0.00。 | P1 | CP-055 | True |
| TP-056 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：已有功能，数值限制大于0.00（场景10） | 页面可直接观察到来源规则所述结果：已有功能，数值限制大于0.00。 | P1 | CP-056 | True |
| TP-057 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | ui_display | 读侧展示：数字选择器，必填；天最大370、时最大23，所有项不可同时为0，后端以秒为单位（场景11） | 页面可直接观察到来源规则所述结果：数字选择器，必填；天最大370、时最大23，所有项不可同时为0，后端以秒为单位。 | P1 | CP-057 | True |
| TP-058 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：original_price; value_constraint（场景2） | 最终业务状态与来源规则一致：original_price; value_constraint。 | P1 | CP-058 | True |
| TP-059 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：current_price; value_constraint（场景2） | 最终业务状态与来源规则一致：current_price; value_constraint。 | P1 | CP-059 | True |
| TP-060 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：service_duration; value_constraint（场景2） | 最终业务状态与来源规则一致：service_duration; value_constraint。 | P1 | CP-060 | True |
| TP-061 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：in_box_sort_order; value_constraint; integer_only=True（场景2） | 最终业务状态与来源规则一致：in_box_sort_order; value_constraint; integer_only=True。 | P1 | CP-061 | True |
| TP-062 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：inventory_warning_threshold; value_constraint; integer_only=True（场景2） | 最终业务状态与来源规则一致：inventory_warning_threshold; value_constraint; integer_only=True。 | P1 | CP-062 | True |
| TP-063 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：purchase_alert_recipient; data_source_constraint; data_source=盒子后台管理员列表（场景2） | 最终业务状态与来源规则一致：purchase_alert_recipient; data_source_constraint; data_source=盒子后台管理员列表。 | P1 | CP-063 | True |
| TP-064 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：cloud_machine_type; data_source_constraint; data_source=盒子现有云机类型（场景2） | 最终业务状态与来源规则一致：cloud_machine_type; data_source_constraint; data_source=盒子现有云机类型。 | P1 | CP-064 | True |
| TP-065 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：promotion_image; value_constraint（场景2） | 最终业务状态与来源规则一致：promotion_image; value_constraint。 | P1 | CP-065 | True |
| TP-066 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：promotion_slogan; value_constraint（场景2） | 最终业务状态与来源规则一致：promotion_slogan; value_constraint。 | P1 | CP-066 | True |
| TP-067 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：performance_parameters; value_constraint（场景2） | 最终业务状态与来源规则一致：performance_parameters; value_constraint。 | P1 | CP-067 | True |
| TP-068 | 云挂机购买页 | 版本Tab | 云挂机购买页 | 版本Tab | field_rule | 业务结果：全新版和常规版两个Tab均可见、可切换并展示对应内容（场景2） | 最终业务状态与来源规则一致：全新版和常规版两个Tab均可见、可切换并展示对应内容。 | P1 | CP-068 | True |
| TP-069 | 云挂机购买页 | 特价专区 | 云挂机购买页 | 特价专区 | field_rule | 业务结果：后台未配置特殊区商品时，C端隐藏整个特价专区（场景2） | 最终业务状态与来源规则一致：后台未配置特殊区商品时，C端隐藏整个特价专区。 | P1 | CP-069 | True |
| TP-070 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：库存不足时同步隐藏商品、停止分配云机并发送告警（场景2） | 最终业务状态与来源规则一致：库存不足时同步隐藏商品、停止分配云机并发送告警。 | P1 | CP-070 | True |
| TP-071 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | field_rule | 业务结果：所有云机类型均需配置宣传内容且云机类型不可重复（场景2） | 最终业务状态与来源规则一致：所有云机类型均需配置宣传内容且云机类型不可重复。 | P1 | CP-071 | True |
| TP-072 | 盒子管理后台-云手机商品管理-添加 | 商品区与库存规则说明表 | 云手机商品管理 | 商品区与库存规则说明表 | cross_surface_linkage | 跨端联动：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知（场景2） | B端、服务端与C端的可观察结果保持一致：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知。 | P0 | CP-072 | True |
| TP-073 | 盒子管理后台-云手机商品管理-添加 | 商品区与库存规则说明表 | 云手机商品管理 | 商品区与库存规则说明表 | cross_surface_linkage | 跨端联动：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知（场景3） | B端、服务端与C端的可观察结果保持一致：库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知。 | P0 | CP-073 | True |
| TP-074 | 盒子管理后台-云手机商品管理-添加 | 商品添加表单 | 云手机商品管理 | 商品添加表单 | cross_surface_linkage | 跨端联动：配置ID、商品名称、云机类型、云机服务时长、通知时间、通知人由配置或系统生成（场景2） | B端、服务端与C端的可观察结果保持一致：配置ID、商品名称、云机类型、云机服务时长、通知时间、通知人由配置或系统生成。 | P0 | CP-074 | True |
| TP-075 | 盒子管理后台-编辑宣传内容 | 宣传内容编辑表单 | 宣传内容管理 | 宣传内容编辑表单 | prompt_display | 提示展示：最多上传5张，支持gif/jpg/jpeg/png，单张最大500K，建议尺寸1008*160（场景2） | 页面展示来源中的建议或提示文案：最多上传5张，支持gif/jpg/jpeg/png，单张最大500K，建议尺寸1008*160；建议内容不作为提交结果判定。 | P2 | CP-075 | True |
