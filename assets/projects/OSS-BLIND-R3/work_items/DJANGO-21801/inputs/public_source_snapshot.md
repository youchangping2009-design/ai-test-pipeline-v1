# Public source snapshot

Captured at: 2026-09-21

## Included input

- GitHub PR: https://github.com/django/django/pull/21801
- Django ticket: https://code.djangoproject.com/ticket/37286
- PR title: `Fixed #37286 -- Preserved unique constraints when removing db_index.`
- PR state at capture: merged

## Public requirement facts used as input

- On MySQL, a field can have both `db_index=True` and a named `UniqueConstraint` for the same column.
- Removing only `db_index=True` must remove the ordinary non-unique index but preserve the unchanged named unique constraint and its enforcing unique index.
- The model continues to declare the constraint, so the database schema must continue enforcing uniqueness after migration.
- The reported affected versions are Django 6.1 and 4.2 with MySQL 8.4.

## Deliberately excluded from blind input

- Changed-file patches, implementation diff, commit contents and regression-test assertions.
- PR comments after the initial requirement description.
- Automated review or AI summary content.
