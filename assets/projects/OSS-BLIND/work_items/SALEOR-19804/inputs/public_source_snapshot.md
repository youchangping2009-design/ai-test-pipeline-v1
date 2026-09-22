# Public source snapshot

Captured at: 2026-09-21

## Included input

- Main-branch port PR: https://github.com/saleor/saleor/pull/19804
- Original PR: https://github.com/saleor/saleor/pull/19794
- Repository/base/head for #19804: `saleor/saleor`, `main` <- `eng-1695-main`
- PR title: `Fix giftCardBulkCreate removing existing tags from previously created gift cards`
- PR state at capture: merged on 2026-09-17

## PR-description facts used as requirement input

- Reusing an existing tag in `giftCardBulkCreate` must not remove that tag from gift cards created earlier.
- New gift cards must be added to the existing tag relation rather than replacing all relations.
- Multiple batches with identical, overlapping, and disjoint tag sets must retain the correct membership for every tag.
- `giftCardCreate` and `giftCardUpdate` are unaffected.
- The fix is forward-only; already lost tag links cannot be reconstructed automatically.
- No migrations or GraphQL schema changes are declared.

## Deliberately excluded from blind input

- Changed-file patches and newly added regression-test assertions.
