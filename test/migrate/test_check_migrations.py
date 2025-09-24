import pytest

from libqtile.scripts.migrations import MIGRATIONS, load_migrations
from test.test_check import have_mypy, is_cpython

pytestmark = pytest.mark.skipif(not is_cpython() or not have_mypy(), reason="needs mypy")

migration_tests = []

# We store a list of test IDs so that tests can be filtered during development
# e.g. pytest -k MigrationID
migration_ids = []

load_migrations()

for m in MIGRATIONS:
    tests = []
    for i, test in enumerate(m.TESTS):
        if not test.check:
            continue
        tests.append((m.ID, test))
        migration_ids.append(f"{m.ID}-{i}")

    if not tests:
        continue

    migration_tests.extend(tests)


@pytest.mark.parametrize("migration_tester", migration_tests, indirect=True, ids=migration_ids)
def test_check_all_migrations(migration_tester):
    migration_tester.assert_check()
