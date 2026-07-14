# Requirement Summary Output Contract

Use this contract when creating `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/requirement_summary.md`.

When source provenance is available, also create or refresh `assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/source_manifest.json`.

## Required Sections

```md
# <WORK_ITEM_ID> <需求标题>需求整理

整理时间：YYYY-MM-DD

## 1. 资料来源
## 2. 需求结论
## 3. 前置条件 / 准备工作
## 4. 业务范围与不做范围
## 5. 面向研发的需求拆解
## 6. 面向测试的验收关注点
## 7. 数据 / 埋点 / 接口 / 配置要求
## 8. 风险与兼容性
## 9. 待确认问题
## 10. 本轮整理边界
```

Rename sections when the domain needs clearer labels, but keep the intent.

## Source Manifest

Use `source_manifest.json` to record requirement source provenance. Keep raw files under `inputs/`; the manifest is only an index and access status record.

```json
{
  "project_code": "<PROJECT_CODE>",
  "work_item_id": "<WORK_ITEM_ID>",
  "manifest_type": "requirement_source_manifest",
  "summary_artifact": "inputs/requirement_summary.md",
  "sources": [
    {
      "source_id": "SRC-001",
      "source_type": "local_file",
      "location": "inputs/需求描述",
      "status": "available",
      "local_artifact": "inputs/需求描述",
      "notes": "原始需求描述"
    }
  ],
  "unresolved_sources": []
}
```

## Writing Rules

- Put the highest-signal conclusion near the top.
- Prefer tables for fields, APIs, domains, versions, environments, statuses, and ownership.
- Use concrete values from sources: URLs, branch names, merge request links, appkey, version numbers, enum values, API paths, callback fields, exact prompts/errors.
- Mark source freshness: use exact dates for chat decisions and public docs when known.
- Record conflicts explicitly: `PRD says ...; 2026-xx-xx chat later confirms ...`.
- Separate product acceptance from risk/API guard items.
- Do not turn soft prompts, UI hints, or optional public-doc capabilities into hard blockers unless sources say so.
- Do not create official testcase language here; this file is input preparation for later pipeline stages.

## Suggested Detail By Source Type

### Local inputs

- Summarize every file that contributes rules or evidence.
- For images, capture visible page names, fields, operations, statuses, prompts, and annotations.
- Preserve unknowns rather than guessing.

### Feishu/Lark docs

- Capture title, update date/revision if available, and source URL.
- Extract product scope, functional scope, fields, pages, flows, assets, and open questions.
- If the doc embeds sheets/base/whiteboards, route to the corresponding skill before summarizing when those embedded resources carry requirements.

### Feishu/Lark group messages

- Read enough history to capture decisions from initial request through latest confirmation.
- Include message dates for decisions that change scope.
- Treat attachments/screenshots as evidence only after inspecting or downloading them.

### Public official/vendor docs

- Extract integration facts needed by development/testing: endpoints, auth, required parameters, response fields, callback/notification behavior, domain allowlists, expiry windows, and error codes.
- Keep quotations short and paraphrase most content.
- Link the official page in the source list.

## Quality Checklist

- The document answers: who/what/where/when/how/what not to do.
- Developers can identify affected modules, fields, APIs, branches, and config.
- Testers can identify environments, C端/B端/API/埋点/兼容性 coverage areas.
- Pending questions are actionable and tied to impact.
- No downstream artifacts are modified unless explicitly requested.
