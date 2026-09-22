# KUBERNETES-141831 公开需求快照

- 来源：https://github.com/kubernetes/kubernetes/pull/141831
- 标题：resource: warn on empty DeviceTaintRule selector
- 状态：已合并
- 目标分支：`master`
- 作者：`yogeshbendre`
- 冻结日期：2026-09-22

## 可作为需求输入的行为事实

- `DeviceTaintRule.spec.deviceSelector` 存在但 driver、pool、device 均为空时，会匹配集群中每个 driver 的每个 device。
- create 和 update 均应返回非阻塞 Warning response header，且不受 taint effect 取值影响。
- selector 省略（nil）时不告警；空对象 `{}` 时返回精确警告：`spec.deviceSelector: an empty selector matches every device from every driver in the cluster`。
- selector 指定 driver、pool 或 device 时不告警。
- 警告不得阻止创建/更新、要求确认或改变校验与执行语义。
- `kubectl --warnings-as-errors` 可因警告返回非零状态，但对象仍已创建。

## 盲测隔离

本快照不包含代码 diff、注册路径、实现 hook、自动化测试、现场验证、提交或 Review 评论。上述信息仅允许在后续 Oracle 阶段使用。
