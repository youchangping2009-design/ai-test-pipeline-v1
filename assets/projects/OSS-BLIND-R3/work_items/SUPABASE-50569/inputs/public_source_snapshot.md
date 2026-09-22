# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/supabase/supabase/pull/50569
- PR title: `Recovery codes: allow users to use recovery codes to access their account`
- PR state at capture: merged

## PR-description facts used as requirement input

- A user redirected to MFA verification can choose recovery-code authentication.
- A valid recovery code signs the user in and consumes one available recovery code.
- The recovery-code entry is shown only when recovery codes are available and the feature configuration is enabled.
- When the feature configuration is disabled, the entry is hidden and direct access to the recovery-code sign-in page redirects to the MFA page.

## Deliberately excluded from blind input

- Changed-file patches, commit contents and test implementation.
- Automated CodeRabbit summary in the PR body.
- Undocumented UI fields, error messages and validation rules.
