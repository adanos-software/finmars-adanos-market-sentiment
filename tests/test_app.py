from __future__ import annotations

from fastapi.testclient import TestClient

from finmars_adanos_connector.app import create_app, get_adanos_client, get_settings
from finmars_adanos_connector.adanos import AdanosClientError
from finmars_adanos_connector.models import SentimentRecord, Source
from finmars_adanos_connector.settings import Settings


class FakeAdanosClient:
    async def fetch_compare(
        self,
        *,
        symbols: list[str],
        source: Source,
        days: int,
        api_key: str,
        base_url: str,
    ) -> list[SentimentRecord]:
        assert api_key == "sk_live_env"
        assert base_url == "https://api.adanos.org"
        return [
            SentimentRecord(symbol=symbol, sentiment_score=0.3, buzz_score=60, mentions=5)
            for symbol in symbols
        ]


class FailingAdanosClient:
    async def fetch_compare(self, **_: object) -> list[SentimentRecord]:
        raise AdanosClientError("upstream unavailable")


def _client(
    *,
    connector_token: str | None = None,
    adanos_api_key: str | None = "sk_live_env",
    fake_client: object | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        adanos_api_key=adanos_api_key,
        adanos_base_url="https://api.adanos.org",
        connector_token=connector_token,
        request_timeout_seconds=20.0,
    )
    app.dependency_overrides[get_adanos_client] = lambda: fake_client or FakeAdanosClient()
    return TestClient(app)


def test_simple_import_endpoint_returns_flat_rows() -> None:
    response = _client().post(
        "/v1/finmars/simple-import/sentiment",
        json={"symbols": ["TSLA"], "source": "news_stocks"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["data"][0]["Instrument"] == "TSLA"
    assert payload["data"][0]["Adanos Sentiment Score"] == 0.3


def test_connector_token_is_enforced_when_configured() -> None:
    client = _client(connector_token="secret")

    rejected = client.post(
        "/v1/finmars/simple-import/sentiment",
        json={"symbols": ["TSLA"]},
    )
    accepted = client.post(
        "/v1/finmars/simple-import/sentiment",
        headers={"X-Connector-Token": "secret"},
        json={"symbols": ["TSLA"]},
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 200


def test_missing_adanos_api_key_returns_clear_direct_error() -> None:
    response = _client(adanos_api_key=None).post(
        "/v1/finmars/simple-import/sentiment",
        json={"symbols": ["TSLA"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "ADANOS_API_KEY is not configured"


def test_universal_endpoint_returns_finmars_envelope() -> None:
    response = _client().post(
        "/v1/finmars/universal/sentiment",
        json={
            "id": "run-1",
            "user": {"token": "finmars-user-token"},
            "scheme_name": "adanos_market_sentiment",
            "scheme_type": "simple_import",
            "options": {"symbols": "TSLA,NVDA", "adanos_source": "news_stocks"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "run-1"
    assert payload["provider"] == "adanos"
    assert payload["error_status"] == 0
    assert [row["Instrument"] for row in payload["data"]] == ["TSLA", "NVDA"]


def test_universal_endpoint_returns_error_envelope_for_upstream_failures() -> None:
    response = _client(fake_client=FailingAdanosClient()).post(
        "/v1/finmars/universal/sentiment",
        json={
            "id": "run-2",
            "user": {"token": "finmars-user-token"},
            "scheme_name": "adanos_market_sentiment",
            "scheme_type": "simple_import",
            "options": {"symbols": "TSLA", "adanos_source": "news_stocks"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "run-2"
    assert payload["error_status"] == 1
    assert "upstream unavailable" in payload["error_message"]
