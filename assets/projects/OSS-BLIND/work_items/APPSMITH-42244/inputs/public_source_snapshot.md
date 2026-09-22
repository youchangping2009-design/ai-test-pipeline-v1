# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/appsmithorg/appsmith/pull/42244
- Repository/base/head: `appsmithorg/appsmith`, `release` <- `fix/app-15972`
- PR title: `fix: validate Databricks JDBC connections`
- PR state at capture: merged on 2026-09-17

## PR-description facts used as requirement input

- Validate custom Databricks JDBC URLs before creating a connection.
- Use the Databricks JDBC driver directly and fail closed when it rejects the URL.
- Reject non-Databricks URLs while preserving valid Databricks connections, including customized `jdbc:databricks://` configurations.
- Existing valid installations and upgrades should be unchanged.
- Rollback requires no data or configuration migration.
- Suggested review entry point: `DatabricksPluginExecutor.datasourceCreate`.

## Deliberately excluded from blind input

- Changed-file patches and newly added regression-test assertions.
- Automated third-party PR summaries.
- Details from the linked private Linear issue.
- Details from the linked advisory, because its public API response was unavailable during capture.
