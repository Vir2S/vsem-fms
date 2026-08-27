from vsem_fms.app.config import Settings


def test_legacy_max_file_size_environment_name_is_supported(monkeypatch):
    monkeypatch.delenv("MAX_FILE_SIZE_MB", raising=False)
    monkeypatch.setenv("MAX_FILE_SIZE", "7")
    monkeypatch.setenv("API_KEY", "test-api-key-0123456789")

    config = Settings(_env_file=None)

    assert config.MAX_FILE_SIZE_MB == 7


def test_canonical_max_file_size_name_takes_precedence(monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE", "7")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "11")
    monkeypatch.setenv("API_KEY", "test-api-key-0123456789")

    config = Settings(_env_file=None)

    assert config.MAX_FILE_SIZE_MB == 11
