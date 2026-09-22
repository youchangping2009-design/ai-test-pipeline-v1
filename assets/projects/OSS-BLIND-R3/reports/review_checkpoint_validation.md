# Harness Review Checkpoint 修复验证

日期：2026-09-22

## 修复

Review 阶段由无命令 checkpoint 改为 validation：

1. 所有工作项执行 design feedback validator，并要求 `design/design_feedback.json` 存在。
2. 任一 Oracle 资产存在时，要求 freeze/input/score 三件套完整。
3. 校验冻结清单路径安全、资产 SHA-256 和 `oracle_excluded_from_generation=true`。
4. 使用当前 Oracle input 与正式 testcase 只读重算，要求现有 score 除时间戳外完全一致。
5. Review fingerprint 纳入 design feedback 与三份 Oracle 文件，内容变化会使旧 checkpoint 失效并重新执行。

反馈全部 applied 后允许非需求资产相对原始冻结基线变化，用于兼容反馈回灌后的复测；requirement summary 漂移始终失败。

## 四份 R3 验证

| 样本 | Review attempt | Validator commands | Freeze | Requirement coverage | 结果 |
|---|---:|---:|---|---:|---|
| Django #21801 | 2 | 2 | intact | 1.0 | PASS |
| Celery #10668 | 2 | 2 | intact | 0.9444 | PASS |
| Temporal #11968 | 2 | 2 | intact | 1.0 | PASS |
| Supabase #50569 | 2 | 2 | intact | 1.0 | PASS |

四个 run 均在 Review succeeded 后暂停，Strict Gate 保持 pending；run audit 4/4 通过。

## 负向回归

- 冻结资产在反馈 applied 前漂移：失败。
- Oracle score 与当前 input/testcase 重算不一致：失败。
- Oracle 文件变化：Review fingerprint 变化，必须重跑。
- 历史第一批反馈已全部 applied：允许保留原始冻结清单并识别为 post-feedback regeneration。
