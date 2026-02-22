from datetime import datetime
from unittest.mock import patch

import pytest

from bot.db.models import Message
from bot.services.analyzer import _parse_json, analyze_messages
from bot.utils.text import format_message, format_messages


def _make_msg(msg_id: int, text: str, user: str = "Alice", reply_to: int | None = None) -> Message:
    return Message(
        id=None,
        source_id=1,
        message_id=msg_id,
        user_id=42,
        user_name=user,
        text=text,
        reply_to_message_id=reply_to,
        date=datetime(2025, 1, 20, 10, 0),
    )


def test_format_message_basic():
    msg = _make_msg(100, "Hello world")
    result = format_message(msg)
    assert "[2025-01-20 10:00]" in result
    assert "Alice" in result
    assert "(#msg:100)" in result
    assert "Hello world" in result


def test_format_message_with_reply():
    msg = _make_msg(101, "I agree", reply_to=100)
    result = format_message(msg)
    assert "[→100]" in result


def test_format_messages():
    msgs = [_make_msg(1, "A"), _make_msg(2, "B")]
    result = format_messages(msgs)
    assert "(#msg:1)" in result
    assert "(#msg:2)" in result


def test_parse_json_direct():
    raw = '{"important_topics": [], "discussed_topics": [], "week_stats": {}}'
    result = _parse_json(raw)
    assert result is not None
    assert result["important_topics"] == []


def test_parse_json_markdown_block():
    raw = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
    result = _parse_json(raw)
    assert result == {"key": "value"}


def test_parse_json_embedded_braces():
    raw = 'Here is the result: {"a": 1} end'
    result = _parse_json(raw)
    assert result == {"a": 1}


def test_parse_json_invalid():
    assert _parse_json("no json here") is None


VALID_RESPONSE = """{
  "important_topics": [
    {"title": "Test", "summary": "Sum", "first_message_id": 1, "participants": ["Alice"]}
  ],
  "discussed_topics": [],
  "week_stats": {"total_messages": 5, "active_users": 2, "most_active_user": "Alice"}
}"""


@patch("bot.services.analyzer._call_replicate")
async def test_analyze_messages_single_pass(mock_call):
    mock_call.return_value = VALID_RESPONSE
    msgs = [_make_msg(i, f"text {i}") for i in range(5)]

    result = await analyze_messages(msgs)

    assert len(result["important_topics"]) == 1
    assert result["important_topics"][0]["title"] == "Test"
    mock_call.assert_called_once()


async def test_analyze_messages_empty():
    result = await analyze_messages([])
    assert result["important_topics"] == []
    assert result["week_stats"]["total_messages"] == 0
