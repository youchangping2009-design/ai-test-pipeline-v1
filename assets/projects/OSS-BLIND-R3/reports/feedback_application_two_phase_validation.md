# Feedback Application 两阶段工作流验证

日期：2026-09-22

## 结论

反馈回灌不再需要人工填写 before hash。标准流程必须先冻结目标设计层，再修改设计产物，最后由工具生成 receipt 并更新反馈状态。

## 命令

```bash
/usr/bin/python3 scripts/manage_feedback_application.py prepare \
  --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --feedback-id DF-001

# 仅修改 feedback.target_layer 对应的设计产物

/usr/bin/python3 scripts/manage_feedback_application.py record \
  --project-code <PROJECT_CODE> --work-item-id <WORK_ITEM_ID> --feedback-id DF-001
```

## 安全约束

- prepare 仅接受 `accepted` feedback。
- 目标只能是 feedback 声明设计层的标准文件，不能选择正式 testcase。
- 已有 baseline snapshot 不允许覆盖。
- record 前 feedback 内容、目标层和身份必须与 snapshot 一致。
- 没有真实文件变化时不能生成 receipt。
- 写入顺序为 receipt first、status second；中断后重复 record 可幂等收口。
- 若已有其它 applied feedback 缺 receipt，本次 record 在写入前失败。

## 验证

- 两阶段正常流程：PASS。
- `testcases/testcases_main.md` 越界目标：拒绝。
- 未修改目标设计产物直接 record：拒绝。
- prepare 后修改 feedback 内容：拒绝。
- receipt 已写、状态未更新后的重复 record：PASS。
- 与 feedback receipt / Review 联合聚焦测试：18/18 PASS。
- 全量质量基线：5/5 PASS，157 项单测通过。
