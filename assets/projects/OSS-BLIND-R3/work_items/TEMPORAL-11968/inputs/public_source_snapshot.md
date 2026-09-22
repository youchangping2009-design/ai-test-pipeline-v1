# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/temporalio/temporal/pull/11968
- PR title: `Fix SignalWithStart request ID deduplication after execution closes`
- PR state at capture: merged

## PR-description facts used as requirement input

- Retrying `SignalWithStart` with the same request ID after the original workflow closes can start a new run and send a duplicate signal.
- The retry must return the original run instead of starting another workflow run.
- The retry must not send the signal a second time.
- Deduplicated `SignalWithStart` starts should be observable through a dedicated metric.

## Deliberately excluded from blind input

- Changed-file patches, commit contents and unit/functional test assertions.
- Internal implementation path and test fixtures not stated as public behavior.
- Automated summaries and later review comments.
