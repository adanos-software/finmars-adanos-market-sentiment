from __future__ import annotations

from finmars_adanos_connector.settings import load_settings


def test_load_settings_trims_env_values(monkeypatch) -> None:
    monkeypatch.setenv("ADANOS_API_KEY", " sk_live_test ")
    monkeypatch.setenv("ADANOS_BASE_URL", " https://api.adanos.org/ ")
    monkeypatch.setenv("FINMARS_CONNECTOR_TOKEN", " token ")
    monkeypatch.setenv("ADANOS_TIMEOUT_SECONDS", "2.5")

    settings = load_settings()

    assert settings.adanos_api_key == "sk_live_test"
    assert settings.adanos_base_url == "https://api.adanos.org/"
    assert settings.connector_token == "token"
    assert settings.request_timeout_seconds == 2.5


def test_load_settings_handles_empty_and_invalid_env_values(monkeypatch) -> None:
    monkeypatch.setenv("ADANOS_API_KEY", " ")
    monkeypatch.setenv("ADANOS_BASE_URL", " ")
    monkeypatch.setenv("FINMARS_CONNECTOR_TOKEN", "")
    monkeypatch.setenv("ADANOS_TIMEOUT_SECONDS", "invalid")

    settings = load_settings()

    assert settings.adanos_api_key is None
    assert settings.adanos_base_url == "https://api.adanos.org"
    assert settings.connector_token is None
    assert settings.request_timeout_seconds == 20.0


def test_load_settings_rejects_non_positive_timeouts(monkeypatch) -> None:
    monkeypatch.setenv("ADANOS_TIMEOUT_SECONDS", "0")

    settings = load_settings()

    assert settings.request_timeout_seconds == 20.0
