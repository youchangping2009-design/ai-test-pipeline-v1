---
name: requirement-summary
description: Project-scoped AI Test Pipeline skill for creating or refreshing a work item inputs/requirement_summary.md from local inputs, Feishu/Lark documents or group messages, public vendor documentation, screenshots, prototypes, and user-provided supplementary material. Use in this repository when the user asks to 理解需求, 整理需求, 生成 requirement_summary.md, combine inputs files with external資料, or prepare a development and testing oriented requirement summary before structured_prd/testcase generation.
---

# Requirement Summary

## Scope

Create a local, reviewable `requirement_summary.md` under:

```text
assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/requirement_summary.md
```

This skill is for the current `ai-test-pipeline-v1` project environment. It stops at requirement understanding and input normalization. Do not generate or update `structured_prd`, `case_plan`, `testcases`, traceability, or business code unless the user explicitly asks for that next stage.

When `inputs/requirement_summary.md` exists, `prd-structuring` should treat it as the preferred consolidated input over scattered raw files.

As part of the main pipeline, always create or refresh:

```text
assets/projects/<PROJECT_CODE>/work_items/<WORK_ITEM_ID>/inputs/source_manifest.json
```

`source_manifest.json` records where each source came from and whether it was available, pending auth, failed, or skipped. It is an input provenance aid, not a replacement for raw `inputs/` files.

The reasoning stage consumes both files: confirmed requirement sections become explicit reasoning rules, and source manifest entries become provenance notes. Image evidence remains optional for text-only requirements.

## Required Startup

Before work, read the project protocol files in this order:

1. `START_HERE.md`
2. `WORKFLOW_CONTRACT.md`
3. `docs/roadmap/NEXT_ACTION.md`
4. `docs/roadmap/WORK_QUEUE.md`
5. `docs/roadmap/DECISION_LOG.md`

Then inspect the target work item:

```bash
/usr/bin/python3 skills/requirement-summary/scripts/inventory_inputs.py \
  --project-code <PROJECT_CODE> \
  --work-item-id <WORK_ITEM_ID>
```

Use the script output to see existing `inputs/` files, screenshots, drafts, and whether `requirement_summary.md` already exists.

## Source Order

Prefer source-backed facts over memory or inference:

1. Existing local files under the work item `inputs/`.
2. User-provided links and chat IDs in the current request.
3. Feishu/Lark documents, group messages, images, and attachments when referenced.
4. Public official/vendor documentation for external platform behavior.
5. Project code or branches only when the user asks to combine code evidence.

When sources conflict, keep both with dates and mark the latest explicit confirmation as the current working assumption. Do not silently overwrite older PRD text with chat conclusions.

## Public Practice Rules

Use public internet material only when it improves implementation or testing understanding. Prefer:

- Official vendor docs, product docs, API references, migration guides, and release notes.
- Public examples from the platform owner that show a successful integration path.
- Stable interface facts: endpoints, required fields, auth/signature requirements, callback behavior, constraints, and error codes.

Avoid:

- Copying long vendor documentation into the output.
- Treating blogs, forum posts, or AI-generated snippets as authoritative.
- Mixing unrelated platform products into scope because they share a brand name.

If an external document is a JavaScript app, extract its embedded data or use browser inspection rather than summarizing only the landing HTML. Record access limits if the content requires login or cannot be fetched.

## Workflow

1. Determine `<PROJECT_CODE>` and `<WORK_ITEM_ID>` from the user, cwd, or path. If not discoverable, ask one short question.
2. Run the inventory script and read all relevant local `inputs/` files. For screenshots, inspect images directly; do not rely only on filenames.
3. Fetch referenced Feishu/Lark docs and chat messages using the matching Lark skills. For chats, paginate until the relevant discussion is covered, and expand/download resources only when they affect requirements.
4. Fetch public official/vendor docs when the user asks for public practice or when the external platform behavior is important to implementation/testing.
5. Synthesize a development-and-testing oriented summary, not a marketing recap.
6. Write or refresh `inputs/requirement_summary.md` with the structure in `references/output-contract.md`.
7. Write or refresh `inputs/source_manifest.json` with every source actually consumed in this run.
8. Update root `PROGRESS.md` with a concise record: sources read, output path, validation command, and scope boundary.
9. Run at least:

```bash
/usr/bin/python3 scripts/run_quality_baseline.py
```

If the user only requested the input summary, do not run strict work item validation unless there are existing downstream artifacts you intentionally changed.

## Output Expectations

Read `references/output-contract.md` before writing the Markdown. The document must:

- Be useful to both developers and testers.
- Separate confirmed requirements, inferred assumptions, risks, and pending questions.
- Include concrete pages, fields, APIs, parameters, statuses, versions, branches, domains, and error messages when available.
- Preserve out-of-scope boundaries.
- Use absolute source dates for chat-derived decisions.
- Avoid inventing mandatory validation, blocker behavior, fields, callbacks, or UI states.

## Completion

Before final response:

- Confirm `inputs/requirement_summary.md` exists and is non-empty.
- Confirm `skills/requirement-summary/scripts/validate_requirement_sources.py --input <source_manifest.json> --strict` passes.
- Confirm `PROGRESS.md` was updated.
- Report validation result.
- Mention any unreadable sources or remaining confirmation gaps.
