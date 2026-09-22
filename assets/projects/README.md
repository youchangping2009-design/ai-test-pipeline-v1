# Projects

业务项目资产放在 `assets/projects/<PROJECT_CODE>/`。

项目根采用轻量壳：`project_manifest.json`、`inputs/common/`、`indexes/`、`reports/`、`knowledge/` 和 `work_items/`。正式测试资产只存在于工作项目录。

`assets/projects/` 下的工作项是业务样本与历史产物，不是 strict gate 或 quality baseline 的默认依赖。框架基线只使用 `evals/fixtures/` 中的通用夹具；业务工作项必须通过命令行显式指定后单独校验。其他项目工作项请在本地或业务仓自行初始化，不建议把大量历史实战资产长期提交进流程仓。

初始化命令见根目录 `README.md` 与 `docs/operating_sop.md`。
