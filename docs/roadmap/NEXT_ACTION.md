# Next Action

```yaml
task_id: P3-001
title: testcase_bundle.json compatibility-only projection
status: done
priority: P3
owner: autonomous_agent
```

## Goal

新增 `testcase_bundle.json` 作为从 `testcases_main.md` 派生的 compatibility-only 结构化投影，不切换 testcase 真源。

## Scope

- 新增 `testcase_bundle` schema、生成脚本和校验脚本。
- `validate_work_item.py` 在 bundle 存在时校验它与 `testcases_main.md` 一致。
- 更新 strict 正向样例的 `testcases/testcase_bundle.json`。
- 明确当前 `testcases/testcases_main.md` 仍是主 testcase 真源。

## Out Of Scope

- 不切换 testcase 真源。
- 不改旧导出链路。
- 不大范围重写 testcase/schema。
- 不修改业务代码。

## Validation

至少运行：

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

至少运行总基线，并运行 `validate_testcase_bundle.py` 与 `validate_work_item.py` 正向样例。

## Completion Notes

P2-002 已新增 `scripts/run_evals.py --all` 和 fixture 索引，并通过 `scripts/run_evals.py --all` 与 `scripts/run_quality_baseline.py`。

P3-001 compatibility-only 阶段已完成。`testcase_bundle.json` 是从 `testcases_main.md` 派生的投影，`projection_only=true`，当前不作为 testcase 真源。

Queue drain check completed on 2026-04-28: `WORK_QUEUE.md` 当前无 `todo` 任务，`HUMAN_ACTION_REQUIRED.md` 当前无阻塞问题。后续新增任务应先写入 `WORK_QUEUE.md` 或更新本文件。

Ad-hoc PT081 closeout completed on 2026-04-28: 已完成本次四仓 dev 拉取后 PT081 相关更新清单、12 条真实 CRUD 用例预期收敛、PT081 自动校验与覆盖/质量总结产物。主用例真源仍为 `testcases/testcases_main.md`，未修改任何前后端业务代码。

Ad-hoc PT083 closeout completed on 2026-04-29: 清理重复工作项文件集 `PT083_STRICT_PASS`，当前 PT083 正式工作项承担 strict 正向样例与交付真源角色。主用例真源仍为 `testcases/testcases_main.md`，未修改任何业务代码。

Ad-hoc PT081 rerun stability check completed on 2026-04-29: 已备份 PT081 testcase、清理旧用例派生产物并重跑用例产出链路。纯规则重跑确定性稳定但完整性不稳定，会从 141 条回退到 111 条并漏掉 30 条补强用例；已恢复补强用例并重新通过 PT081 校验。后续应把后台配置页真实 CRUD 等补强项沉淀到正式生成规则或设计层。

Ad-hoc PT081 generic rule hardening completed on 2026-04-29: 已把 PT081 30 条补强用例来源沉淀为后台配置页通用生成规则，覆盖真实 CRUD、容量限制、展示频次、跨字段约束、数据源过滤+排序组合与 Flow 预期去泛化。清理 PT081 派生产物后纯重跑产出 153 条主用例，`validate_work_item` 通过。

Ad-hoc PT083 rerun stability check completed on 2026-04-29: 已备份 PT083 当前用例并通过 regeneration bundle existing-provider 回放重跑。新旧 `testcases_main.md`、`testcase_bundle.json` hash 完全一致，主用例 18 条、case_plan 21 条保持不变；已补齐缺失的 `reviews/duplicate_case_report.json` 派生产物，`validate_work_item --strict --work-item-level L` 与 `run_quality_baseline.py` 均通过。

Ad-hoc testcase grouping rules completed on 2026-04-29: 已沉淀 `rules/testcase_grouping_rules.md`，将 `section_name` 纳入 coverage matrix 可选字段并从 structured_prd 传递到 testcase row，新增 `validate_testcase_grouping.py` 与 `CASE_GROUPING` eval。当前 `testcases_main.md` 仍是主 testcase 真源，分表依据为 `page_name + section_name`，未修改任何业务代码。

Ad-hoc PT083 artifact cleanup and testcase rerun completed on 2026-04-29: 已清理 PT083 可再生历史产物 11 项，并通过 regeneration bundle 回放重建 `testcases_main.md`、兼容镜像、审计产物、traceability adapter、feishu 导出与 testcase bundle。当前主用例保持 18 条、4 个页面/板块表，`validate_work_item --strict --work-item-level L` 与 `run_quality_baseline.py` 均通过。

Ad-hoc SC0963 testcase rerun completed on 2026-04-29: 已备份 SC0963 旧版 testcase，清理旧流程派生产物，并补齐 `testability_gate`、`case_plan` 与 `testcase_bundle`。原始当前 coverage 生成器重跑仅产出 26 条且存在重复编号、弱板块和 coverage 缺口；已恢复为 33 条高信号主用例并追加 `来源 CasePlan：CP-xxx` 追溯。`testcase_lint`、`validate_testability_gate`、`validate_case_plan`、`validate_testcase_bundle`、structured_prd schema 与主 traceability 均通过。工作项级 `validate_work_item` 仍被既有 evidence/image_evidence 枚举兼容问题阻塞，已写入 `HUMAN_ACTION_REQUIRED.md`。

Ad-hoc SC0963 grouping refinement completed on 2026-04-29: 已按用户期望将 SC0963 主用例分组从模糊“规则用例表”调整为业务层级：`页游落地页管理 / 页游落地页列表-筛选条件`、`页游落地页列表-操作按钮`、`新建页游单游戏落地页`、`新建页游多游戏聚合页`。同步更新 `structured_prd.modules[].features[].section_name` 与 `coverage_matrix.entries[].section_name`，并在 `rules/testcase_grouping_rules.md` 沉淀产品描述型需求的“业务域页面 + 子页面/功能模块”分组规则。`testcase_grouping --strict`、`testcase_lint`、`validate_case_plan`、`validate_testcase_bundle` 与 `run_quality_baseline.py` 均通过；SC0963 工作项级校验仍只被既有 evidence/image_evidence 枚举兼容问题阻塞。

Ad-hoc SC0963 new-flow rerun comparison completed on 2026-04-29: 已按用户要求清理 SC0963 可再生产物并冻结原始 `testcases/testcases_main.md`（MD5 `5624bf9553dfcc1466ba7177743404ed`，未修改）。新流程候选输出到 `.generation/rerun-new-flow-20260429-1605/`，候选产出 26 条、唯一 coverage 22/33、5 张表；分组 strict 通过但 lint 失败，存在 10 个重复编号、2 个 Flow 终态不足，且仍额外生成 `小程序首页改版页 / 跨板块主流程`。结论：候选不能替代原始 33 条交付真源，应作为 coverage->testcase 生成器缺陷证据继续修复。

Ad-hoc SC0963 coverage testcase generator hardening completed on 2026-04-29: 已修复 `coverage_testcase_generator.py` 与 `generate_testcases_from_coverage.py`，使 Flow 用例继承业务域页面 `页游落地页管理`，用例编号使用稳定页面/模块编码并全局去重，coverage->testcase 保留图片规格、枚举、默认值、必填、二次确认、数据源过滤和长度上限等高信号断言。带 `case_plan.json` 生成时仅保留可追溯 CasePlan 的候选用例。SC0963 新候选输出到 `.generation/rerun-generator-fix-20260429/`，33 条、33/33 coverage、33/33 CasePlan、4 张表，`testcase_lint`、`testcase_grouping --strict`、`validate_case_plan` 与 `run_quality_baseline.py` 均通过；原始 `testcases/testcases_main.md` 保持 MD5 `5624bf9553dfcc1466ba7177743404ed`，未修改。

Ad-hoc SC0965 current-flow rerun completed on 2026-04-29: 已备份 SC0965 旧版用例，清理可再生历史产物，并补齐 `testability_gate`、`case_plan` 与 `testcase_bundle`。首次重跑发现 `coverage_type=data_rule` 未生成正式用例，导致 `COV-EX-0015` 聚合版位注册均分漏失；已在 `coverage_testcase_generator.py` 增加通用数据规则分支后重跑。新版主用例 20 条、coverage 20/20、CasePlan 20/20，`validate_work_item --strict --work-item-level S --retention minimal` 与 `run_quality_baseline.py` 均通过；新旧差异报告见 `assets/projects/AD/work_items/SC0965/reviews/sc0965_testcase_rerun_comparison.md`。

Ad-hoc testcase copy readability hardening completed on 2026-04-29: 已将 testcase 生成文案从字段名/coverage title 直出调整为人类可读元素名与规则语义渲染，覆盖标题、前置条件、测试步骤、预期结果；机器字段继续只保留在备注追溯中。新增 `testcase_lint.py` 正文 `snake_case` 泄漏检查。SC0965 重跑后 20 条主用例在标题/步骤/预期中不再暴露机器字段；SC0963 抽检 33 条通过新增 lint。`validate_work_item --strict --work-item-level S --retention minimal` 与 `run_quality_baseline.py` 均通过。

Ad-hoc default non-required rule completed on 2026-04-29: 已将“需求未描述必填/必选且原型无 `*` 或等价标识时，默认非必填”写入 AGENTS、结构化 prompt、用例生成 prompt、case-generation skill 与 testcase signal policy。`coverage_testcase_generator.py` 已改为只有明确必填证据时才生成“为空保存失败 / 不可提交 / 必填拦截”断言。清理 SC0965 历史可再生产物后重跑，筛选字段预期无必填断言，`filter_required_bad_count=0`；`validate_work_item --strict --work-item-level S --retention minimal` 与 `run_quality_baseline.py` 均通过。

Ad-hoc developer self-test testcase projection completed on 2026-04-29: 已新增 `testcases/dev_self_testcases.md` 作为从 `testcases/testcases_main.md` 过滤 `开发必测` 标签得到的派生 Markdown，不新增 JSON，不切换 testcase 真源。生成链路已在 `generate_testcases_from_coverage.py` 与 regeneration post normalizer 中自动刷新该文件；PT083、SC0963、SC0965、PT081 当前样例均已派生并通过来源一致性抽查。

Ad-hoc tag semantic refinement and AD rerun completed on 2026-04-29: 已按“自动化执行载体”和“人工执行责任”拆分标签语义，不新增标签类型。`AI-API用例 / AI-UI用例` 表示适合沉淀的执行载体，非核心稳定自动化用例不再默认追加 `测试必测 / 开发必测`；核心流程或关键变更必须同时包含 `开发必测` 与 `测试必测`。SC0963 与 SC0965 已清理可再生产物并按新规则重跑：SC0963 主用例 33 条、开发自测 4 条；SC0965 主用例 20 条、开发自测 2 条。`testcase_lint`、`validate_case_plan`、`validate_testcase_bundle`、`validate_work_item`(SC0965)、PT083 strict、`run_quality_baseline.py` 与 `run_evals.py --all` 均通过；SC0963 工作项级校验仍仅被既有 evidence/image_evidence 历史枚举兼容问题阻塞。

Ad-hoc SC0963 input-only regeneration completed on 2026-04-29: 用户清空 SC0963 旧产物并仅保留 input 后，已重新初始化工作项产物，基于输入重建 `structured_prd`、`image_evidence`、`testability_gate`、`coverage_matrix`、`case_plan`、`testcases_main.md`、`dev_self_testcases.md`、`testcase_bundle`、traceability、飞书导出与 review 质量产物。当前主用例 33 条，开发自测派生 4 条，coverage/CasePlan 追溯 33/33，主 traceability false_traceability_rate=0.0。`testcase_lint`、`validate_testcase_grouping --strict`、`validate_testability_gate`、`validate_case_plan`、`validate_testcase_bundle`、`validate_image_evidence`、`validate_image_evidence_mapping`、`validate_work_item --strict --work-item-level S --retention minimal --skip-code-reviews` 与 `run_quality_baseline.py` 均通过；本轮未执行代码映证，因当前未提供前后端代码目录和人工确认。

Ad-hoc README update for 2026-04-29 refactor completed on 2026-04-29: 已分析当天改造主线并更新根 `README.md`，补充标签语义拆分、开发自测派生、coverage->testcase 生成器增强、用例元素定义规则与基线命令。未修改业务代码。

Ad-hoc human readable testcase style completed on 2026-05-19: 已新增 `rules/testcase_human_readable_style.md`，将人工可读表达风格接入 AGENTS、START_HERE、WORKFLOW_CONTRACT、workflow、operating_sop 与 structured_to_cases prompt，并最小调整 `coverage_testcase_generator.py` 的字段/值标注和抽象预期表达。未修改业务代码，未切换 testcase 真源，`run_quality_baseline.py` 通过。

Ad-hoc SC0970 human-readable testcase optimization completed on 2026-05-19: 已按 `rules/testcase_human_readable_style.md` 优化 SC0970 45 条正式用例表达，保持用例数量、coverage 追溯与优先级不变；同步刷新 `testcases/testcases.md`、`testcases/smoke_test_开发必测.md`、`testcases/testcase_bundle.json`、`traceability/coverage_first_traceability.json`、`traceability/traceability_adapter.json`、`reviews/quality_report.json` 与 `reviews/review_record.md`。`validate_work_item --project-code AD --work-item-id SC0970 --skip-code-reviews` 与 `run_quality_baseline.py` 通过。

Ad-hoc SC0972 initialization blocked on 2026-05-22: 已创建 `assets/projects/AD/work_items/SC0972/` 并检查 `inputs/`；当前仅有初始化 README，未提供 PRD、截图或补充材料。已按“不脑补规则”口径生成空 `structured_prd`、空主用例、空 `coverage_first_traceability` 与阻塞型 review 记录，并将真实阻塞写入 `docs/roadmap/HUMAN_ACTION_REQUIRED.md`。`validate_work_item --project-code AD --work-item-id SC0972 --skip-code-reviews` 与 `run_quality_baseline.py` 通过；当前不可作为正式测试交付。

Ad-hoc SC0972 testcase generation completed on 2026-05-22: 用户补充 `inputs/需求描述` 后，已重新生成 SC0972 结构化 PRD、testability gate、acceptance examples、case_plan、19 条 `testcases/testcases_main.md` 主用例、开发自测派生、testcase bundle、coverage-first 追溯与 review 记录。当前覆盖推广计划头条2.0素材列表、创编素材池、头条素材数据列表与投放策略素材清理四个页面/板块；未对未说明的多选、必填、Toast、清理触发按钮和执行频率做脑补断言。`validate_work_item --project-code AD --work-item-id SC0972 --skip-code-reviews --strict --work-item-level M --retention minimal --check-element-notation` 与 `run_quality_baseline.py` 均通过。

Ad-hoc SC0970 attribution requirement update completed on 2026-05-25: 已按用户调整将 SC0970 归因方式从统一{注册归因}更新为按“游戏类型”区分：{小游戏}使用{注册归因}，{应用推广}使用{激活归因}。同步更新 `inputs/需求描述`、`structured_prd`、`coverage_matrix`、`testcases/testcases_main.md`、兼容镜像、`testcase_bundle.json`、coverage-first traceability、traceability adapter、review 质量产物与 SC0970 再生成脚本；主用例仍为 45 条，未修改任何业务代码。`validate_work_item --project-code AD --work-item-id SC0970 --skip-code-reviews` 与 `run_quality_baseline.py` 均通过。

Ad-hoc requirement source intake and testpoints projection completed on 2026-07-13: 已将多源输入归一化文件名统一为 `inputs/requirement_summary.md`，新增 `inputs/source_manifest.json` 来源清单 schema/校验入口，并新增从 `testcases/case_plan.json` 派生的 `testcases/testpoints.md` / `testpoints.json` 评审视图。新增能力不切换 `case_plan`、`testcases_main.md` 或 traceability 真源。`validate_work_item --project-code WX-YGJ --work-item-id PT083 --skip-code-reviews --strict` 与 `run_quality_baseline.py` 均通过。

Ad-hoc main-pipeline intake, synchronized testpoints and persisted work-item level completed on 2026-07-21: `requirement_summary.md` / `source_manifest.json` 已提升为 strict 主流程输入阶段，`testpoints.*` 已与正式 testcase 同轮生成并由 bundle 后处理自动刷新；`manifest.json.work_item_level` 成为长期档位配置，CLI 仅做本轮覆盖且有效档位会传递到最终校验。PT083 已登记为 L 档并补齐真实需求摘要、来源清单和同步测试点。

Ad-hoc pipeline consumer closure completed on 2026-07-22: reasoning 已消费 requirement summary/source manifest 并支持纯文本需求；任务包已拆出 testability、acceptance、test design、case plan 阶段；L bundle 强制完整设计层；post-write 自动刷新 testpoints、dev self、testcase bundle、traceability 和 quality report；quality report 新增主产物指纹；CR findings 可生成 design feedback。PT083 strict 与总基线通过；其 coverage_matrix 当前为空，规则生成器现会硬失败以防空结果覆盖既有 18 条正式用例。

Ad-hoc stage validator co-location completed on 2026-07-27: Requirement Sources、Reasoning Pack、Coverage Matrix 单阶段 validator 已迁入 `skills/<skill>/scripts/`，并新增 reasoning-analysis 与 coverage-planning Skill。任务包、统一校验和 Skill 文档已改用新路径；PT083 验证通过后已删除旧 Requirement 根入口，Reasoning/Coverage 继续保留兼容 wrapper。

Ad-hoc lightweight project shell completed on 2026-07-27: 项目根已收敛为 project manifest、`inputs/common`、indexes、reports、knowledge 和 work_items；新增项目视图刷新与项目校验入口，移除 `validate_outputs.py` 和 WX-YGJ 项目级空占位产物。PT083 工作项真源与路径保持不变。

Ad-hoc host-neutral core cleanup completed on 2026-07-27: AGENTS、自驱动协议、Roadmap 和 repair 模板已改为通用 Agent 表述；任务包不再硬引用 Cursor adapter；三份宿主 README 已对齐；删除 Codex agent YAML 与 runtime bridge。所有宿主统一使用显式 `ATP_*` 运行时配置，核心不自动探测任何宿主。
