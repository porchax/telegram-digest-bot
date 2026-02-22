from datetime import datetime, timedelta

import pytest

from bot.db.models import Digest, Message, Source
from bot.db.repository import Repository


@pytest.fixture
def repo():
    return Repository()


async def test_get_or_create_source(repo):
    source = await repo.get_or_create_source(
        telegram_id=-1001234567890,
        source_type="group",
        title="Test Group",
        username=None,
    )
    assert source.id is not None
    assert source.telegram_id == -1001234567890
    assert source.type == "group"
    assert source.title == "Test Group"


async def test_get_or_create_source_idempotent(repo):
    s1 = await repo.get_or_create_source(-100111, "group", "G1")
    s2 = await repo.get_or_create_source(-100111, "group", "G1")
    assert s1.id == s2.id


async def test_get_or_create_source_updates_title(repo):
    s1 = await repo.get_or_create_source(-100222, "group", "Old")
    s2 = await repo.get_or_create_source(-100222, "group", "New")
    assert s2.title == "New"
    assert s1.id == s2.id


async def test_save_and_get_messages(repo):
    source = await repo.get_or_create_source(-100333, "group", "G")
    now = datetime.utcnow()

    msg = Message(
        id=None,
        source_id=source.id,
        message_id=1,
        user_id=42,
        user_name="Alice",
        text="Hello",
        reply_to_message_id=None,
        date=now,
    )
    await repo.save_message(msg)

    messages = await repo.get_messages(
        source.id,
        now - timedelta(hours=1),
        now + timedelta(hours=1),
    )
    assert len(messages) == 1
    assert messages[0].text == "Hello"
    assert messages[0].user_name == "Alice"


async def test_save_message_duplicate_ignored(repo):
    source = await repo.get_or_create_source(-100444, "group", "G")
    now = datetime.utcnow()

    msg = Message(
        id=None, source_id=source.id, message_id=10,
        user_id=1, user_name="Bob", text="Hi",
        reply_to_message_id=None, date=now,
    )
    await repo.save_message(msg)
    await repo.save_message(msg)  # duplicate

    count = await repo.get_message_count(source.id)
    assert count == 1


async def test_get_message_count_with_dates(repo):
    source = await repo.get_or_create_source(-100555, "group", "G")
    now = datetime.utcnow()

    for i in range(5):
        await repo.save_message(Message(
            id=None, source_id=source.id, message_id=i,
            user_id=1, user_name="X", text=f"msg{i}",
            reply_to_message_id=None,
            date=now - timedelta(days=i),
        ))

    total = await repo.get_message_count(source.id)
    assert total == 5

    recent = await repo.get_message_count(
        source.id,
        now - timedelta(days=2),
        now + timedelta(hours=1),
    )
    assert recent == 3


async def test_save_and_get_digest(repo):
    source = await repo.get_or_create_source(-100666, "group", "G")
    now = datetime.utcnow()

    digest = Digest(
        id=None,
        source_id=source.id,
        week_start=now - timedelta(days=7),
        week_end=now,
        content="Test digest",
        message_count=42,
    )
    digest_id = await repo.save_digest(digest)
    assert digest_id > 0

    last = await repo.get_last_digest(source.id)
    assert last is not None
    assert last.content == "Test digest"
    assert last.message_count == 42
