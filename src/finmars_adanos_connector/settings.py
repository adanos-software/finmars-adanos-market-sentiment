from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    adanos_api_key: str | None
    adanos_base_url: str
    connector_token: str | None
    request_timeout_seconds: float


def load_settings() -> Settings:
    return Settings(
        adanos_api_key=_clean_optional_env("ADANOS_API_KEY"),
        adanos_base_url=_clean_env("ADANOS_BASE_URL", "https://api.adanos.org"),
        connector_token=_clean_optional_env("FINMARS_CONNECTOR_TOKEN"),
        request_timeout_seconds=_request_timeout_seconds(),
    )


def _clean_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip() or default


def _clean_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip() or None


def _request_timeout_seconds() -> float:
    timeout = os.getenv("ADANOS_TIMEOUT_SECONDS", "20")
    try:
        seconds = float(timeout)
    except ValueError:
        return 20.0
    return seconds if seconds > 0 else 20.0
