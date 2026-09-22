# Testability Gate

| gate_id | source_rule_id | classification | testability | decision | confidence | source_text | reason |
|---|---|---|---|---|---|---|---|
| TG-001 | OBJ-001 | product_behavior | testable | generate_acceptance_example | confirmed | promotion_slogan; value_constraint | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-002 | OBJ-002 | product_behavior | testable | generate_acceptance_example | confirmed | performance_parameters; value_constraint | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-003 | OBJ-003 | product_behavior | testable | generate_acceptance_example | confirmed | 后台未配置特殊区商品时隐藏 | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-004 | FR-云挂机购买页-特价专区-01 | product_behavior | testable | generate_acceptance_example | confirmed | 最多展示4个商品 | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-005 | OBJ-004 | product_behavior | partially_testable | generate_acceptance_example | confirmed | original_price; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-006 | OBJ-005 | product_behavior | partially_testable | generate_acceptance_example | confirmed | current_price; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-007 | OBJ-006 | product_behavior | partially_testable | generate_acceptance_example | confirmed | service_duration; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-008 | OBJ-007 | product_behavior | partially_testable | generate_acceptance_example | confirmed | in_box_sort_order; value_constraint; integer_only=True | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-009 | OBJ-008 | product_behavior | partially_testable | generate_acceptance_example | confirmed | inventory_warning_threshold; value_constraint; integer_only=True | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-010 | OBJ-009 | product_behavior | partially_testable | generate_acceptance_example | confirmed | purchase_alert_recipient; data_source_constraint; data_source=盒子后台管理员列表 | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-011 | FR-盒子管理后台-云手机商品管理-添加-商品添加表单-01 | field_constraint | testable | generate_acceptance_example | confirmed | 天数最大370，小时最大23，所有项不可同时为0，后端以秒为单位 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-012 | FR-盒子管理后台-云手机商品管理-添加-商品添加表单-02 | field_constraint | testable | generate_acceptance_example | confirmed | 特殊区商品数量必须小于等于4，超过4个时不可保存 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-013 | FR-盒子管理后台-云手机商品管理-添加-商品添加表单-03 | field_constraint | testable | generate_acceptance_example | confirmed | 正整数，上限1000；相同排序值按创建时间倒序排列 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-014 | FR-盒子管理后台-云手机商品管理-添加-商品添加表单-04 | backend_job | testable | generate_acceptance_example | confirmed | 正整数，上限200；按固定频率校验库存是否小于等于配置数量 | 可通过库存任务或报警结果验证，保留执行频率待确认边界。 |
| TG-015 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-01 | linkage | testable | generate_acceptance_example | confirmed | 库存小于等于预警值时，C端隐藏商品、不分配云机并发送库存不足通知 | 可通过后台配置、C端展示/分配和通知结果验证跨端联动。 |
| TG-016 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-02 | field_constraint | testable | generate_acceptance_example | confirmed | 已有功能，数值限制大于0.00 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-017 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-03 | field_constraint | testable | generate_acceptance_example | confirmed | 已有功能，数值限制大于0.00 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-018 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-04 | field_constraint | testable | generate_acceptance_example | confirmed | 数字选择器，必填；天最大370、时最大23，所有项不可同时为0，后端以秒为单位 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-019 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-05 | field_constraint | testable | generate_acceptance_example | confirmed | 下拉单选，必填，content：特殊区、普通区；特殊区商品数量小于等于4 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-020 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-06 | field_constraint | testable | generate_acceptance_example | confirmed | 数字框，必填，正整数，上限1000；相同值按创建时间倒序 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-021 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-07 | product_behavior | testable | generate_acceptance_example | confirmed | 已有功能，增加未配置提示；服务时长结束后C端不再展示 | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-022 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-08 | field_constraint | testable | generate_acceptance_example | confirmed | 数字框，非必填，正整数，上限200；按固定频率校验库存 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-023 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-09 | field_constraint | testable | generate_acceptance_example | confirmed | 下拉单选，必填，content：盒子后台管理员列表 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-024 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-10 | backend_job | testable | generate_acceptance_example | confirmed | 云手机相关报警 | 可通过库存任务或报警结果验证，保留执行频率待确认边界。 |
| TG-025 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-11 | field_constraint | testable | generate_acceptance_example | confirmed | 【云挂机库存不足通知】 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-026 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-12 | field_constraint | testable | generate_acceptance_example | confirmed | 玩心盒子后台_云挂机_云手机商品管理 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-027 | FR-盒子管理后台-云手机商品管理-添加-商品区与库存规则说明表-13 | linkage | testable | generate_acceptance_example | confirmed | 配置ID、商品名称、云机类型、云机服务时长、通知时间、通知人由配置或系统生成 | 可通过后台配置、C端展示/分配和通知结果验证跨端联动。 |
| TG-028 | OBJ-010 | product_behavior | partially_testable | generate_acceptance_example | confirmed | cloud_machine_type; data_source_constraint; data_source=盒子现有云机类型 | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-029 | OBJ-011 | product_behavior | testable | generate_acceptance_example | confirmed | promotion_image; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-030 | OBJ-012 | product_behavior | testable | generate_acceptance_example | confirmed | promotion_slogan; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-031 | OBJ-013 | product_behavior | testable | generate_acceptance_example | confirmed | performance_parameters; value_constraint | 产品行为有来源规则和可观察结果；涉及跨页面或既有逻辑时按部分可测保留边界。 |
| TG-032 | FR-盒子管理后台-编辑宣传内容-宣传内容编辑表单-01 | field_constraint | testable | generate_acceptance_example | confirmed | 保存前校验所有云机类型均已配置且不存在重复 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-033 | FR-盒子管理后台-编辑宣传内容-宣传内容编辑表单-02 | soft_prompt | partially_testable | generate_acceptance_example | confirmed | 最多上传5张，支持gif/jpg/jpeg/png，单张最大500K，建议尺寸1008*160 | 只验证建议或提示展示，不把建议尺寸升级为上传、保存或提交失败。 |
| TG-034 | FR-盒子管理后台-编辑宣传内容-宣传内容编辑表单-03 | product_behavior | testable | generate_acceptance_example | confirmed | 文本长度20个字符；C端超过一行换行展示 | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-035 | FR-盒子管理后台-编辑宣传内容-宣传内容编辑表单-04 | product_behavior | testable | generate_acceptance_example | confirmed | 文本长度20个字符；C端超过一行换行展示 | 规则描述的是读侧展示、隐藏或换行结果，不包含保存拦截语义。 |
| TG-036 | FR-盒子管理后台-编辑宣传内容-宣传内容字段说明表-01 | field_constraint | testable | generate_acceptance_example | confirmed | 下拉列表框，必填，默认为空，可编辑；单选，content为盒子现有云机类型 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-037 | FR-盒子管理后台-编辑宣传内容-宣传内容字段说明表-02 | soft_prompt | partially_testable | generate_acceptance_example | confirmed | 图片按钮，必传，最多5张；支持gif/jpg/jpeg/png，最大500K，建议尺寸1008*160；支持拖拽和删除 | 只验证建议或提示展示，不把建议尺寸升级为上传、保存或提交失败。 |
| TG-038 | FR-盒子管理后台-编辑宣传内容-宣传内容字段说明表-03 | field_constraint | testable | generate_acceptance_example | confirmed | 文本框，必填，20个字符；C端超过一行换行展示 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-039 | FR-盒子管理后台-编辑宣传内容-宣传内容字段说明表-04 | field_constraint | testable | generate_acceptance_example | confirmed | 文本框，必填，20个字符；C端超过一行换行展示 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-040 | FR-盒子管理后台-编辑宣传内容-宣传内容字段说明表-05 | field_constraint | testable | generate_acceptance_example | confirmed | 点击增加一条宣传配置，最多额外新增1块；达到2条时禁用按钮 | 字段必填、范围、长度、格式、数量或数据源规则具备明确可观察结果。 |
| TG-041 | TECH-001 | technical_background | needs_confirmation | needs_confirmation | unknown | 云机SDK目标版本、发布范围和回滚方案未明确。 | 缺少稳定验收口径或边界，不能生成confirmed强断言。 |
| TG-042 | TECH-002 | technical_background | needs_confirmation | needs_confirmation | unknown | 画面模糊和卡顿缺少帧率、延迟、码率、丢帧或主观评分阈值。 | 缺少稳定验收口径或边界，不能生成confirmed强断言。 |
| TG-043 | TECH-003 | technical_background | needs_confirmation | needs_confirmation | unknown | 720*1280尚未明确是系统、渲染还是客户端展示分辨率。 | 缺少稳定验收口径或边界，不能生成confirmed强断言。 |
| TG-044 | TECH-004 | technical_background | needs_confirmation | needs_confirmation | unknown | 脚本类型、接入方式及与720*1280的兼容范围未明确。 | 缺少稳定验收口径或边界，不能生成confirmed强断言。 |
| TG-045 | TECH-005 | technical_background | needs_confirmation | needs_confirmation | unknown | 库存校验固定频率、并发下单、重复告警及恢复展示口径未明确。 | 缺少稳定验收口径或边界，不能生成confirmed强断言。 |
| TG-046 | TECH-006 | technical_background | out_of_scope | out_of_scope | confirmed | MVP历史覆盖、破冰率和后续购买数据属于活动复盘背景，不是本期功能验收。 | 当前输入仅提供背景或未展开内容，不进入本期产品验收。 |
| TG-047 | TECH-007 | technical_background | out_of_scope | out_of_scope | confirmed | 商品编辑弹窗和商品顺序编辑弹窗未展开，不能补写未知交互。 | 当前输入仅提供背景或未展开内容，不进入本期产品验收。 |
| TG-048 | TECH-008 | technical_background | out_of_scope | out_of_scope | confirmed | 既有下拉字段完整枚举、默认值及未展示数据源不在当前输入范围内。 | 当前输入仅提供背景或未展开内容，不进入本期产品验收。 |
| TG-049 | COV-EX-0050 | product_behavior | testable | generate_acceptance_example | confirmed | 全新版和常规版两个Tab均可见、可切换并展示对应内容。 | Coverage中的独立业务结果未被单字段Gate完整表达，需要单独验收标准。 |
| TG-050 | COV-EX-0060 | product_behavior | testable | generate_acceptance_example | confirmed | 后台未配置特殊区商品时，C端隐藏整个特价专区。 | Coverage中的独立业务结果未被单字段Gate完整表达，需要单独验收标准。 |
| TG-051 | COV-EX-0067 | product_behavior | testable | generate_acceptance_example | confirmed | 库存不足时同步隐藏商品、停止分配云机并发送告警。 | Coverage中的独立业务结果未被单字段Gate完整表达，需要单独验收标准。 |
| TG-052 | COV-EX-0070 | product_behavior | testable | generate_acceptance_example | confirmed | 所有云机类型均需配置宣传内容且云机类型不可重复。 | Coverage中的独立业务结果未被单字段Gate完整表达，需要单独验收标准。 |
| TG-053 | AMB-PROD-001 | product_behavior | needs_confirmation | needs_confirmation | unknown | 免费体验用户资格、次数、有效期及是否需要支付未明确。 | 产品行为缺少来源口径，不能脑补正式断言。 |
| TG-054 | AMB-PROD-002 | product_behavior | needs_confirmation | needs_confirmation | unknown | 全新版与常规版的云机类型对应关系和切换默认态未明确。 | 产品行为缺少来源口径，不能脑补正式断言。 |
| TG-055 | AMB-PROD-003 | product_behavior | needs_confirmation | needs_confirmation | unknown | 宣传图片多张时是否轮播、轮播顺序和间隔未明确。 | 产品行为缺少来源口径，不能脑补正式断言。 |
| TG-056 | AMB-PROD-004 | product_behavior | needs_confirmation | needs_confirmation | unknown | 商品展示时间的输入控件、时区和起止边界未明确。 | 产品行为缺少来源口径，不能脑补正式断言。 |
| TG-057 | AMB-PROD-005 | product_behavior | needs_confirmation | needs_confirmation | unknown | 购买数量报警通知人的可选范围、多人选择及删除规则未明确。 | 产品行为缺少来源口径，不能脑补正式断言。 |
| TG-058 | RISK-001 | risk_hardening | risk_only | risk_note_only | confirmed | 需求要求更新云机SDK以改善画面模糊和卡顿，但未提供目标版本、帧率、延迟、码率、丢帧或主观评分阈值，当前无法形成稳定的通过或失败判定。 | 风险只进入设计加固与人工复核，不混入product acceptance主链。 |
| TG-059 | RISK-002 | risk_hardening | risk_only | risk_note_only | confirmed | 需求明确画面尺寸调整为720*1280，但未说明其是云机系统分辨率、渲染分辨率还是客户端展示容器，也未说明旋转、缩放、触控映射和终端适配边界。 | 风险只进入设计加固与人工复核，不混入product acceptance主链。 |
| TG-060 | RISK-003 | risk_hardening | risk_only | risk_note_only | confirmed | 库存阈值会同时影响C端商品隐藏、云机停止分配和管理员告警，但校验频率文字模糊，且未说明并发下单、缓存延迟、重复告警和恢复展示口径。 | 风险只进入设计加固与人工复核，不混入product acceptance主链。 |
| TG-061 | RISK-004 | risk_hardening | risk_only | risk_note_only | confirmed | B端特殊区最多配置4个商品，C端特价专区也最多展示4个商品；若保存校验、状态口径或C端消费不同步，可能出现可保存但不展示或超量展示。 | 风险只进入设计加固与人工复核，不混入product acceptance主链。 |
| TG-062 | RISK-005 | risk_hardening | risk_only | risk_note_only | confirmed | 商品编辑弹窗、商品顺序编辑弹窗、多个下拉字段完整枚举与默认值均未展示，后续结构化若直接按添加表单或当前选中值推断，会形成错误字段和硬校验。 | 风险只进入设计加固与人工复核，不混入product acceptance主链。 |
