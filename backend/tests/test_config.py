from app.core.config import BACKEND_DIR, Settings


def make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@host/db?sslmode=require",
        **overrides,
    )


def test_cors_origins_are_split_and_trimmed():
    settings = make_settings(cors_origins="http://a.test, http://b.test ,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_relative_storage_dir_resolves_against_backend_dir():
    settings = make_settings(storage_dir="storage")

    assert settings.storage_path == BACKEND_DIR / "storage"


def test_absolute_storage_dir_is_kept(tmp_path):
    settings = make_settings(storage_dir=str(tmp_path))

    assert settings.storage_path == tmp_path
