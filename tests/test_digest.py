from datetime import datetime

from bot.services.digest import _format_date_range, format_digest_html
from bot.utils.message_links import make_message_link


def test_make_message_link_public():
    link = make_message_link(-1001234567890, 42, username="mygroup")
    assert link == "https://t.me/mygroup/42"


def test_make_message_link_private():
    link = make_message_link(-1001234567890, 42)
    assert link == "https://t.me/c/1234567890/42"


def test_format_date_range_same_month():
    start = datetime(2025, 1, 13)
    end = datetime(2025, 1, 19)
    assert _format_date_range(start, end) == "13–19 января 2025"


def test_format_date_range_cross_month():
    start = datetime(2025, 1, 28)
    end = datetime(2025, 2, 3)
    result = _format_date_range(start, end)
    assert "января" in result
    assert "февраля" in result


def test_format_digest_html_basic():
    data = {
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
        },
    }

    html = format_digest_html(
        data,
        datetime(2025, 1, 13),
        datetime(2025, 1, 19),
        chat_id=-1001234567890,
        username=None,
    )

    assert "Дайджест недели" in html
    assert "Дедлайн" in html
    assert "Фреймворк" in html
    assert "15 сообщений" in html
    assert "https://t.me/c/1234567890/100" in html
    assert "Сообщений: 50" in html


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
