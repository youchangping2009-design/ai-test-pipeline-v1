# Code Review

- stage: `frontend_code_review`
- review_type: `frontend_code`
- manual_confirmation_required: `true`
- review_policy: `不得修改业务代码，不得修改历史产出物`

## Review Scope

- 对照对象：结构化 PRD / testcase / 当前阶段代码实现
- 输出目标：识别代码缺口、用例缺口、无效用例、仅 PRD 存在但代码未落地项
- 本阶段不得修改业务代码，不得修改历史产出物

## Findings

| 序号 | 类型 | 描述 | 严重级别 | 证据 |
|------|------|------|----------|------|
| 1 | 待补充 |  | P1/P2/P3 |  |

## Coverage Mapping

- 补充需要映证的 `implementation_binding / recommended_cr_stage / manual_confirmation_required / cr_focus_points`

## Invalid Or Stale Cases

- 标记当前代码下无效、过期、无法由本阶段代码证明的用例

## Manual Confirmation

- 需要人工确认后才能作为正式 CR 结论进入流水线
- 人工确认完成后，请同步填写对应 confirmation JSON
