from bot.config import Settings


def test_image_settings_defaults():
    # _env_file=None изолирует тест от локального .env, os.environ всё равно читается
    s = Settings(_env_file=None)
    assert s.generate_digest_image is False
    assert s.image_model == "openai/gpt-image-2"
    assert s.image_quality == "medium"
    assert s.image_output_format == "jpeg"
