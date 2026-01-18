import pytest

from libqtile.scripts.migrations import MIGRATIONS, load_migrations

migration_tests = []

# We store a list of test IDs so that tests can be filtered during development
# e.g. pytest -k MigrationID
migration_ids = []

load_migrations()

for m in MIGRATIONS:
    tests = []
    for i, test in enumerate(m.TESTS):
        tests.append((m.ID, test))
        migration_ids.append(f"{m.ID}-{i}")

    if not tests:
        tests.append((m.ID, None))
        migration_ids.append(f"{m.ID}-no-tests")

    migration_tests.extend(tests)


@pytest.mark.parametrize("migration_tester", migration_tests, indirect=True, ids=migration_ids)
def test_all_migrations(migration_tester):
    # If the migration is expected to result in a change then it should also provide linting
    if migration_tester.test.needs_lint:
        migration_tester.assert_lint(), "No linting provided"

    # Tests whether the expected output is returned by the migration
    migration_tester.assert_migrate()
