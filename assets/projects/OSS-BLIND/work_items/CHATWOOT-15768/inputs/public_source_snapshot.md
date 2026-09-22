# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/chatwoot/chatwoot/pull/15768
- Related issue: https://github.com/chatwoot/chatwoot/issues/15767
- Repository/base/head: `chatwoot/chatwoot`, `develop` <- `fix/filter-type-coercion-inbox-id`
- PR title: `fix(dashboard): resolve type mismatch in conversation filter matching (#15767)`
- PR state at capture: merged on 2026-09-18

## PR-description facts used as requirement input

- Number custom attributes must use numeric filter inputs.
- Values `0` and `false` are valid explicit values and must not be treated as missing.
- Conversation matching keeps strict equality; the change must not stringify every attribute.
- Equal and not-equal filtering must behave consistently for number and checkbox custom attributes.
- Existing saved filters containing string values are not migrated.
- Fresh UI verification was still pending in the PR description.

## Context-only issue facts

- Issue #15767 documents a count/list divergence caused by client-side filtering and an inbox ID string/number mismatch.
- The PR states that inbox-ID mismatch was fixed separately; this sample targets the remaining custom-attribute cases.

## Deliberately excluded from blind input

- Changed-file patches and newly added test assertions.
