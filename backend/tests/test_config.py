from app.core.config import Settings


def make_settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@host/db?sslmode=require",
        **overrides,
    )


def test_cors_origins_are_split_and_trimmed():
    settings = make_settings(cors_origins="http://a.test, http://b.test ,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]
