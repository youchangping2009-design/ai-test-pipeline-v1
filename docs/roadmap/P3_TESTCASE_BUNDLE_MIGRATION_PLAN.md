# P3 Testcase Bundle Migration Plan

## Status

Compatibility-only phase accepted and implemented.

## Current Truth Source

`testcases/testcases_main.md` remains the main testcase truth source.

Current compatibility assets:

- `testcases/testcases.md` is a compatibility mirror.
- `testcases/case_plan.json` is the test design plan before formal testcase generation.
- `feishu_ready.md` is a reading/export artifact, not a testcase truth source.

## Proposed Future State

Introduce `testcases/testcase_bundle.json` as a structured testcase bundle projection. It is generated from `testcases_main.md` and must not replace the truth source in this phase.

Potential migration path:

1. Add schema and template for `testcase_bundle.json`. Done.
2. Generate `testcase_bundle.json` from existing `testcases_main.md` as a compatibility projection. Done.
3. Validate bundle and markdown stay equivalent. Done.
4. Keep `testcases_main.md` as truth source. Done.
5. Future phase, if approved: render `testcases_main.md`, `testcases.md`, and Feishu output from the bundle.
6. Future phase, if approved: switch truth-source wording from markdown-first to bundle-first.

## Future Human Decision

Before a future truth-source switch, the user or project owner must decide:

- Whether P3 should actually switch testcase truth source from `testcases_main.md` to `testcase_bundle.json`.
- Whether migration should be project-wide or limited to new work items first.
- Whether old work items need backfill or can remain markdown-first.

## Current Decision

The user accepted the compatibility-only phase. `testcase_bundle.json` is now a projection generated from `testcases_main.md`; markdown remains authoritative.

## Future Blocker

Changing testcase truth source affects validators, exporters, regeneration bundles, traceability builders, and team operating habits. This requires explicit human approval.
