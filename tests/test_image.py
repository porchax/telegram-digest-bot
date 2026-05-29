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


@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
async def test_generate_poster_success(mock_run):
    fake = MagicMock()
    fake.aread = AsyncMock(return_value=b"image-bytes")
    mock_run.return_value = fake

    result = await generate_poster("a funny poster")

    assert result == b"image-bytes"
    mock_run.assert_awaited_once()


@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
async def test_generate_poster_list_output(mock_run):
    fake = MagicMock()
    fake.aread = AsyncMock(return_value=b"img")
    mock_run.return_value = [fake]

    result = await generate_poster("a funny poster")

    assert result == b"img"


@patch("bot.services.image.replicate.async_run", new_callable=AsyncMock)
@patch("bot.services.image.asyncio.sleep", new_callable=AsyncMock)
async def test_generate_poster_failure_returns_none(mock_sleep, mock_run):
    mock_run.side_effect = RuntimeError("api down")

    result = await generate_poster("a funny poster")

    assert result is None
    assert mock_run.await_count == 2  # _IMAGE_RETRIES
    mock_sleep.assert_awaited_once()
