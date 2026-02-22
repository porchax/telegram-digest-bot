import os
import tempfile

import pytest

# Use a temp file for the test database (in-memory doesn't persist across connections)
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()

os.environ["DATABASE_PATH"] = _tmp.name
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("REPLICATE_API_TOKEN", "test-token")
os.environ.setdefault("ADMIN_USER_IDS", "111111111")

from bot.db.database import close_connection, get_connection, init_db, reset_connection  # noqa: E402


@pytest.fixture(autouse=True)
async def _init_test_db():
    """Re-initialize the database for each test (drop + recreate tables)."""
    # Reset singleton so each test gets a fresh connection to the temp DB
    await close_connection()
    reset_connection()

    db = await get_connection()
    await db.execute("DROP TABLE IF EXISTS digests")
    await db.execute("DROP TABLE IF EXISTS messages")
    await db.execute("DROP TABLE IF EXISTS sources")
    await db.commit()

    await init_db()
    yield

    await close_connection()
    reset_connection()


def pytest_sessionfinish(session, exitstatus):
    """Clean up temp database file after test session."""
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
