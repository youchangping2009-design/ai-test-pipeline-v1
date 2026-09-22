# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/celery/celery/pull/10668
- Linked issue: https://github.com/celery/celery/issues/4300
- PR title: `Fix revoked tasks running anyway after mingle merged revoke stamps from another host`
- PR state at capture: merged

## PR-description facts used as requirement input

- Revoked ETA/countdown tasks can run after worker startup synchronization even though the worker logged them as revoked.
- Revocation state is bounded by expiry and maximum size; foreign monotonic-clock stamps can prevent expiry and cause a newly revoked local task to be evicted.
- The problem affects both worker `mingle` exchange and persisted `--statedb` restore after host reboot.
- Received revocation IDs must be interpreted in the receiving worker's clock domain and remain revoked for the configured expiry after receipt.
- Rolling upgrades must be safe when old and new workers exchange revocation state.

## Deliberately excluded from blind input

- Changed-file patches, commit contents and the listed unit-test assertions.
- Test results and implementation line details as proof of correctness.
- Later discussion comments and automated summaries.
