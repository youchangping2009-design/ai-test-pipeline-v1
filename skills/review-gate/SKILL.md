# Review Gate Skill

## 目标

对 `structured_prd`、`testcases`、`review_record` 和 checklist 执行统一质量门校验，并沉淀人工 review 过程。

该技能对应仓库中的 `Case Reviewer` 角色。

---

## 输入

主要输入：

- `structured_prd.json`
- `testcases_main.md`
- `testcases.md`（兼容镜像）
- `review_record.md`
- `manual_review_checklist.md`

辅助输入：

- lint 报错
- schema 报错
- review 问题列表

---

## 输出

输出可以分为两类：

### 1. 校验结论

来自：

- `review_gate.py`
- `validate_work_item.py`
- `validate_outputs.py`

### 2. 评审沉淀

写入：

- `reviews/review_record.md`

---

## 关联资源

提示词：

- `prompts/review_fix_prompt.md`

检查清单：

- `skills/review-gate/checklists/manual_review_checklist.md`

脚本：

- `skills/review-gate/scripts/review_gate.py`

相关统一入口：

- `scripts/validate_outputs.py`
- `scripts/validate_work_item.py`

---

## 执行步骤

### 1. 执行 structured_prd 校验

检查：

- schema 是否通过
- Flow 业务规则是否通过
- `main_flow` 是否完整
- Flow 与 modules 映射是否一致

---

### 2. 执行 testcase 校验

检查：

- Markdown 表头
- 必填列
- 编号唯一性
- 优先级合法性
- 标题 / 步骤 / 预期结果质量
- 流程型用例特殊要求

---

### 3. 执行 checklist 检查

检查：

- checklist 文件是否存在
- 是否包含关键章节
  - `Flow 结构评审`
  - `流程型用例评审`
  - `编号 / 标签 / 优先级评审`

---

### 4. 执行人工 review

参考 `manual_review_checklist.md`，重点关注：

- Flow 基础完整性
- Flow 提取合理性
- Flow 与 modules 映射关系
- Flow steps 质量
- checkpoint / success_criteria
- 流程型用例质量
- 编号 / 标签 / 优先级

---

### 5. 沉淀 review_record

至少补齐：

- `评审结论`
- `问题清单`

问题清单要尽量清晰描述：

- 问题位置
- 问题类型
- 严重级别
- 建议修订

---

### 6. 必要时触发修订

如校验失败或人工 review 不通过，应使用：

- `prompts/review_fix_prompt.md`

对以下内容进行修订：

- structured_prd
- testcase
- review_record

---

## 分层规则

### 初始化阶段宽松

初始化后的空模板允许存在。

### Review 阶段严格

一旦进入 `review_gate.py`：

- testcase 不应只有表头
- 流程类用例必须满足严格规则
- checklist 必须完整

---

## 自检清单

执行 review 前后请自检：

- 是否所有关键 main_flow 都被覆盖
- 是否存在悬空 Flow
- 是否存在泛化 testcase
- 是否存在缺失编号 / 标签 / 优先级
- 是否已记录 review 结论与问题清单

---

## 禁止行为

禁止：

- 只跑脚本，不做人工 review 判断
- 看到报错只记录不修订
- 忽略 Flow 相关问题
- 用空 review_record 进入正式质量门
