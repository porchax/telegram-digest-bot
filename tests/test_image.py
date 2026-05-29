from unittest.mock import AsyncMock, MagicMock, patch

from bot.services.image import (
    DEFAULT_IMAGE_PROMPT,
    build_image_prompt,
    generate_poster,
)


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_returns_string(mock_call):
    mock_call.return_value = "A satirical infographic poster about a big code merge"
    data = {"important_topics": [{"title": "Большой мёрж"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert isinstance(result, str)
    assert result.strip() != ""
    mock_call.assert_awaited_once()


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_truncates_to_limit(mock_call):
    mock_call.return_value = "x" * 5000
    data = {"important_topics": [{"title": "Тема"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert len(result) <= 1000


@patch("bot.services.image._call_replicate", new_callable=AsyncMock)
async def test_build_image_prompt_default_on_error(mock_call):
    mock_call.side_effect = RuntimeError("LLM down")
    data = {"important_topics": [{"title": "Тема"}], "discussed_topics": []}

    result = await build_image_prompt(data)

    assert result == DEFAULT_IMAGE_PROMPT


async def test_build_image_prompt_default_when_no_topics():
    result = await build_image_prompt({"important_topics": [], "discussed_topics": []})
    assert result == DEFAULT_IMAGE_PROMPT
