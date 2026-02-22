import os
import tempfile

import pytest

# Use a temp file for the test database (in-memory doesn't persist across connections)
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()

os.environ["DATABASE_PATH"] = _tmp.name
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("REPLICATE_API_TOKEN", "test-token")

from bot.db.database import get_connection, init_db  # noqa: E402


@pytest.fixture(autouse=True)
async def _init_test_db():
    """Re-initialize the database for each test (drop + recreate tables)."""
    db = await get_connection()
    try:
        await db.execute("DROP TABLE IF EXISTS digests")
        await db.execute("DROP TABLE IF EXISTS messages")
        await db.execute("DROP TABLE IF EXISTS sources")
        await db.commit()
    finally:
        await db.close()

    await init_db()
    yield
