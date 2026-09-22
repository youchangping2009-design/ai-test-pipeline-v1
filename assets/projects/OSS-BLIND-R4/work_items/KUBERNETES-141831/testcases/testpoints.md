# Testpoints View

- Project: `OSS-BLIND-R4`
- Work Item: `KUBERNETES-141831`
- Truth Source: `testcases/case_plan.json`
- Projection Only: `true`

> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.

| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |
|---|---|---|---|---|---|---|---|---|---|---|
| TP-001 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | create 空 deviceSelector 返回 Warning | 创建响应包含空 selector Warning。 | P0 | CP-001 | True |
| TP-002 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | update 空 deviceSelector 返回 Warning | 更新响应包含空 selector Warning。 | P0 | CP-002 | True |
| TP-003 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | prompt_display | 空 selector 返回精确警告文本 | 警告文本逐字等于 `spec.deviceSelector: an empty selector matches every device from every driver in the cluster`。 | P0 | CP-003 | True |
| TP-004 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | 省略 deviceSelector 不返回空 selector Warning | 响应中不存在空 selector Warning。 | P0 | CP-004 | True |
| TP-005 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | selector 指定 driver 时不返回空 selector Warning | 响应中不存在空 selector Warning。 | P0 | CP-005 | True |
| TP-006 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | selector 指定 pool 时不返回空 selector Warning | 响应中不存在空 selector Warning。 | P0 | CP-006 | True |
| TP-007 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | selector 指定 device 时不返回空 selector Warning | 响应中不存在空 selector Warning。 | P0 | CP-007 | True |
| TP-008 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | cross_surface_linkage | 空 selector Warning 不阻止 create 成功 | create 完成后，响应包含空 selector Warning，且服务端可查询到新对象。 | P0 | CP-008 | True |
| TP-009 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | cross_surface_linkage | 空 selector Warning 不阻止 update 成功 | update 完成后，响应包含空 selector Warning，且服务端保存了新版本对象。 | P0 | CP-009 | True |
| TP-010 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | field_rule | 空 selector Warning 不改变既有校验结果 | 两份请求得到相同的既有校验错误；空 selector 只增加 Warning，不改变校验通过或失败结论。 | P0 | CP-010 | True |
| TP-011 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | cross_surface_linkage | 空 selector Warning 不改变持久化和 taint 执行语义 | 持久化与 taint 执行完成后，对象字段与请求一致，且 taint 仍按空 selector 匹配全部设备。 | P0 | CP-011 | True |
| TP-012 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 空选择器判定 | prompt_display | 所有 taint effect 下空 selector 均返回相同 Warning | 每种 effect 的响应都包含同一条空 selector Warning；Warning 是否出现不受 effect 取值影响。 | P0 | CP-012 | True |
| TP-013 | DeviceTaintRule API | 设备选择器告警 | DeviceTaintRule Admission Warning | 非阻塞警告响应 | cross_surface_linkage | warnings-as-errors 返回非零时对象仍已创建 | kubectl 调用完成后因 Warning 返回非零状态，但查询 API Server 时目标对象处于已创建状态。 | P1 | CP-013 | True |
