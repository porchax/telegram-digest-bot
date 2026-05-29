from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import bot.services.digest as digest_mod
from bot.db.models import Message
from bot.db.repository import Repository
from bot.services.digest import (
    _format_date_range,
    _truncate_html,
    format_digest_html,
    format_discussed_html,
    format_important_html,
    format_stats_html,
)
from bot.utils.message_links import make_message_link


def test_make_message_link_public():
    link = make_message_link(-1001234567890, 42, username="mygroup")
    assert link == "https://t.me/mygroup/42"


def test_make_message_link_private():
    link = make_message_link(-1001234567890, 42)
    assert link == "https://t.me/c/1234567890/42"


def test_make_message_link_private_with_100_in_id():
    """Ensure only the -100 prefix is stripped, not embedded '100'."""
    link = make_message_link(-1001001234567, 42)
    assert link == "https://t.me/c/1001234567/42"


def test_format_date_range_same_month():
    start = datetime(2025, 1, 13)
    end = datetime(2025, 1, 19)
    assert _format_date_range(start, end) == "13–19 января 2025"


def test_format_date_range_cross_month():
    start = datetime(2025, 1, 28)
    end = datetime(2025, 2, 3)
    result = _format_date_range(start, end)
    assert result == "28 января – 3 февраля 2025"


def test_format_date_range_cross_year():
    start = datetime(2024, 12, 28)
    end = datetime(2025, 1, 3)
    result = _format_date_range(start, end)
    assert "декабря" in result
    assert "января" in result
    assert "2025" in result


_SAMPLE_DATA = {
    "important_topics": [
        {
            "title": "Дедлайн",
            "summary": "Обсудили сроки",
            "first_message_id": 100,
            "participants": ["Alice"],
        }
    ],
    "discussed_topics": [
        {
            "title": "Фреймворк",
            "summary": "React vs Vue",
            "first_message_id": 200,
            "participants": ["Bob"],
            "message_count": 15,
        }
    ],
    "week_stats": {
        "total_messages": 50,
        "active_users": 5,
        "most_active_user": "Alice",
    },
}

_WEEK_START = datetime(2025, 1, 13)
_WEEK_END = datetime(2025, 1, 19)
_CHAT_ID = -1001234567890


def test_format_digest_html_basic():
    html = format_digest_html(
        _SAMPLE_DATA, _WEEK_START, _WEEK_END, chat_id=_CHAT_ID, username=None,
    )

    assert "Дайджест недели" in html
    assert "Дедлайн" in html
    assert "Фреймворк" in html
    assert "15 сообщений" in html
    assert "https://t.me/c/1234567890/100" in html
    assert "Сообщений: 50" in html


def test_format_digest_html_has_blockquotes():
    html = format_digest_html(
        _SAMPLE_DATA, _WEEK_START, _WEEK_END, chat_id=_CHAT_ID, username=None,
    )
    assert "<blockquote expandable>" in html
    assert "</blockquote>" in html


def test_format_digest_html_escapes_html():
    data = {
        "important_topics": [
            {
                "title": "<script>alert</script>",
                "summary": "A & B",
                "first_message_id": 1,
                "participants": [],
            }
        ],
        "discussed_topics": [],
        "week_stats": {"total_messages": 1, "active_users": 1},
    }

    html = format_digest_html(
        data, datetime(2025, 1, 1), datetime(2025, 1, 7), -100123, None,
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_format_digest_html_missing_title():
    """Topics with missing title should not crash."""
    data = {
        "important_topics": [
            {"summary": "No title here", "first_message_id": 1, "participants": []}
        ],
        "discussed_topics": [],
        "week_stats": {"total_messages": 1, "active_users": 1},
    }
    html = format_digest_html(data, _WEEK_START, _WEEK_END, _CHAT_ID, None)
    assert "No title here" in html


def test_format_important_html():
    html = format_important_html(
        _SAMPLE_DATA, _WEEK_START, _WEEK_END, _CHAT_ID, None,
    )
    assert "Важные темы" in html
    assert "Дедлайн" in html
    assert "Фреймворк" not in html
    assert "<blockquote expandable>" in html


def test_format_important_html_empty():
    data = {**_SAMPLE_DATA, "important_topics": []}
    html = format_important_html(data, _WEEK_START, _WEEK_END, _CHAT_ID, None)
    assert "не выявлено" in html


def test_format_discussed_html():
    html = format_discussed_html(
        _SAMPLE_DATA, _WEEK_START, _WEEK_END, _CHAT_ID, None,
    )
    assert "Обсуждаемые темы" in html
    assert "Фреймворк" in html
    assert "15 сообщений" in html
    assert "Дедлайн" not in html


def test_format_discussed_html_empty():
    data = {**_SAMPLE_DATA, "discussed_topics": []}
    html = format_discussed_html(data, _WEEK_START, _WEEK_END, _CHAT_ID, None)
    assert "не выявлено" in html


def test_format_stats_html():
    html = format_stats_html(_SAMPLE_DATA, _WEEK_START, _WEEK_END)
    assert "Статистика недели" in html
    assert "50" in html
    assert "5" in html
    assert "Alice" in html
    assert "Важных тем: 1" in html
    assert "Обсуждаемых тем: 1" in html


def test_format_stats_html_null_most_active():
    """most_active_user=None should render as dash, not crash."""
    data = {
        "important_topics": [],
        "discussed_topics": [],
        "week_stats": {"total_messages": 0, "active_users": 0, "most_active_user": None},
    }
    html = format_stats_html(data, _WEEK_START, _WEEK_END)
    assert "—" in html


def test_truncate_html_short():
    text = "Short text"
    assert _truncate_html(text) == text


def test_truncate_html_long():
    text = "x" * 5000
    result = _truncate_html(text)
    assert len(result) <= 4096
    assert "…обрезано" in result


_VALID_DATA = {
    "important_topics": [
        {"title": "T", "summary": "S", "first_message_id": 1, "participants": []}
    ],
    "discussed_topics": [],
    "week_stats": {"total_messages": 1, "active_users": 1, "most_active_user": "Alice"},
}


async def _seed_group_with_message():
    repo = Repository()
    source = await repo.get_or_create_source(-100123, "group", title="Test")
    await repo.save_message(
        Message(
            id=None,
            source_id=source.id,
            message_id=1,
            user_id=42,
            user_name="Alice",
            text="hi",
            reply_to_message_id=None,
            date=datetime.now(UTC) - timedelta(days=1),
        )
    )
    return source


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sends_poster_when_enabled(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "funny poster prompt"
    mock_poster.return_value = b"\xff\xd8\xff fake jpeg"

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=555)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    mock_poster.assert_awaited_once()
    mock_prompt.assert_awaited_once()
    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_awaited()


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_skips_poster_when_disabled(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=556)

    with patch.object(digest_mod.settings, "generate_digest_image", False):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    mock_poster.assert_not_awaited()
    bot.send_photo.assert_not_called()
    bot.send_message.assert_awaited()


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sent_when_poster_fails(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "prompt"
    mock_poster.return_value = None  # генерация картинки провалилась

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=557)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    bot.send_photo.assert_not_called()
    bot.send_message.assert_awaited()  # дайджест всё равно ушёл


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sent_when_poster_raises(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "prompt"
    mock_poster.side_effect = RuntimeError("image api exploded")

    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=558)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    bot.send_photo.assert_not_called()
    bot.send_message.assert_awaited()  # дайджест всё равно ушёл, несмотря на исключение


@patch("bot.services.digest.generate_poster", new_callable=AsyncMock)
@patch("bot.services.digest.build_image_prompt", new_callable=AsyncMock)
@patch("bot.services.digest.analyze_messages", new_callable=AsyncMock)
async def test_digest_sent_when_send_photo_fails(mock_analyze, mock_prompt, mock_poster):
    source = await _seed_group_with_message()
    mock_analyze.return_value = _VALID_DATA
    mock_prompt.return_value = "prompt"
    mock_poster.return_value = b"\xff\xd8\xff fake jpeg"

    bot = AsyncMock()
    bot.send_photo.side_effect = RuntimeError("telegram send_photo failed")
    bot.send_message.return_value = MagicMock(message_id=559)

    with patch.object(digest_mod.settings, "generate_digest_image", True):
        await digest_mod.generate_and_send_digest(bot, source.telegram_id)

    bot.send_photo.assert_awaited_once()  # попытка отправить плакат была
    bot.send_message.assert_awaited()  # но дайджест всё равно ушёл
