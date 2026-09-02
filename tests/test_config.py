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


def test_scoped_api_keys_can_replace_legacy_api_key(monkeypatch):
    import hashlib
    import json

    from vsem_fms.app.config import Settings

    secret = "fms_live_configured_0123456789"
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv(
        "API_KEYS",
        json.dumps(
            [
                {
                    "id": "client-a",
                    "name": "Client A",
                    "secret_hash": hashlib.sha256(secret.encode()).hexdigest(),
                    "scopes": ["files:read", "files:list"],
                    "folder_prefix": "client-a/*",
                }
            ]
        ),
    )

    configured = Settings(_env_file=None)

    assert configured.API_KEY is None
    assert configured.API_KEYS[0].id == "client-a"
    assert configured.API_KEYS[0].folder_prefix == "client-a"


def test_api_key_registry_rejects_duplicate_ids(monkeypatch):
    import hashlib
    import json

    import pytest
    from pydantic import ValidationError

    from vsem_fms.app.config import Settings

    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv(
        "API_KEYS",
        json.dumps(
            [
                {
                    "id": "duplicate",
                    "name": "One",
                    "secret_hash": hashlib.sha256(b"one-secret-0123456789").hexdigest(),
                    "scopes": ["files:read"],
                },
                {
                    "id": "duplicate",
                    "name": "Two",
                    "secret_hash": hashlib.sha256(b"two-secret-0123456789").hexdigest(),
                    "scopes": ["files:list"],
                },
            ]
        ),
    )

    with pytest.raises(ValidationError, match="ids must be unique"):
        Settings(_env_file=None)


def test_s3_backend_requires_bucket(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("API_KEY", "test-api-key-0123456789")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET", raising=False)

    with pytest.raises(ValidationError, match="S3_BUCKET is required"):
        Settings(_env_file=None)


def test_s3_static_credentials_must_be_configured_as_pair(monkeypatch):
    import pytest
    from pydantic import ValidationError

    monkeypatch.setenv("API_KEY", "test-api-key-0123456789")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.setenv("S3_ACCESS_KEY", "access")
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="configured together"):
        Settings(_env_file=None)


def test_s3_can_use_default_aws_credential_chain(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-api-key-0123456789")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_SECRET_KEY", raising=False)

    configured = Settings(_env_file=None)

    assert configured.STORAGE_BACKEND == "s3"
    assert configured.S3_BUCKET == "bucket"
    assert configured.S3_ACCESS_KEY is None
