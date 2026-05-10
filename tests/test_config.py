from app.config import Settings


def test_celery_urls_default_to_redis_url(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)

    settings = Settings(_env_file=None)

    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.celery_broker_url == settings.redis_url
    assert settings.celery_result_backend == settings.redis_url


def test_explicit_celery_urls_override_redis_url(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://backend:6379/2")

    settings = Settings(_env_file=None)

    assert settings.celery_broker_url == "redis://broker:6379/1"
    assert settings.celery_result_backend == "redis://backend:6379/2"
