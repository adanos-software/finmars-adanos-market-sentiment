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
    timeout = os.getenv("ADANOS_TIMEOUT_SECONDS", "20")
    try:
        request_timeout_seconds = float(timeout)
    except ValueError:
        request_timeout_seconds = 20.0

    return Settings(
        adanos_api_key=os.getenv("ADANOS_API_KEY"),
        adanos_base_url=os.getenv("ADANOS_BASE_URL", "https://api.adanos.org"),
        connector_token=os.getenv("FINMARS_CONNECTOR_TOKEN"),
        request_timeout_seconds=request_timeout_seconds,
    )

