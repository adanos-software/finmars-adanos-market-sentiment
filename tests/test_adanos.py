from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import httpx

from finmars_adanos_connector.adanos import AdanosClient, normalize_records, normalize_symbol
from finmars_adanos_connector.models import Source


def test_normalize_records_accepts_common_compare_shapes() -> None:
    payload = {
        "stocks": [
            {
                "ticker": "tsla",
                "sentiment_score": "0.41",
                "buzz_score": 72.5,
                "mentions": "31",
                "trend": "rising",
                "bullish_pct": 64,
                "bearish_pct": 18,
                "date": "2026-04-18",
            }
        ]
    }

    records = normalize_records(payload, source=Source.NEWS_STOCKS)

    assert len(records) == 1
    assert records[0].symbol == "TSLA"
    assert records[0].sentiment_score == 0.41
    assert records[0].buzz_score == 72.5
    assert records[0].mentions == 31
    assert records[0].trend == "rising"
    assert records[0].observed_at == "2026-04-18"


def test_normalize_records_accepts_keyed_payloads() -> None:
    records = normalize_records(
        {
            "TSLA": {"sentiment": 0.2, "buzz": 55},
            "NVDA": {"score": 0.7, "mention_count": 14},
        },
        source=Source.REDDIT_STOCKS,
    )

    assert [record.symbol for record in records] == ["TSLA", "NVDA"]
    assert records[0].sentiment_score == 0.2
    assert records[1].mentions == 14


def test_normalize_symbol_strips_crypto_quote_suffixes() -> None:
    assert normalize_symbol("btc-usdt", source=Source.REDDIT_CRYPTO) == "BTC"
    assert normalize_symbol("eth/usd", source=Source.REDDIT_CRYPTO) == "ETH"
    assert normalize_symbol("$TSLA", source=Source.REDDIT_STOCKS) == "TSLA"


def test_fetch_compare_batches_symbols_and_preserves_source_query_key(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeResponse:
        def __init__(self, symbol_csv: str) -> None:
            self._symbol_csv = symbol_csv

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "stocks": [
                    {"ticker": symbol, "sentiment_score": 0.1}
                    for symbol in self._symbol_csv.split(",")
                    if symbol
                ]
            }

    class FakeAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self.base_url = base_url
            self.timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, path: str, *, params: dict, headers: dict) -> FakeResponse:
            calls.append({"path": path, "params": params, "headers": headers})
            return FakeResponse(str(params["tickers"]))

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    records = asyncio.run(
        AdanosClient().fetch_compare(
            symbols=[f"T{i}" for i in range(23)],
            source=Source.NEWS_STOCKS,
            days=14,
            api_key="sk_live_test",
            base_url="https://api.adanos.org/",
        )
    )

    assert len(calls) == 3
    assert [call["path"] for call in calls] == ["/news/stocks/v1/compare"] * 3
    assert calls[0]["params"] == {"tickers": "T0,T1,T2,T3,T4,T5,T6,T7,T8,T9", "days": 14}
    assert calls[2]["params"] == {"tickers": "T20,T21,T22", "days": 14}
    assert calls[0]["headers"] == {"X-API-Key": "sk_live_test"}
    assert [record.symbol for record in records] == [f"T{i}" for i in range(23)]


def test_fetch_compare_uses_symbols_query_key_for_crypto(monkeypatch) -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, json={"tokens": [{"symbol": "BTC-USDT", "sentiment": 0.5}]})

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *, base_url: str, timeout: float) -> None:
            super().__init__(base_url=base_url, timeout=timeout, transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    records = asyncio.run(
        AdanosClient().fetch_compare(
            symbols=["BTC"],
            source=Source.REDDIT_CRYPTO,
            days=7,
            api_key="sk_live_test",
            base_url="https://api.adanos.org",
        )
    )

    parsed = urlparse(requested_urls[0])
    assert parsed.path == "/reddit/crypto/v1/compare"
    assert parse_qs(parsed.query)["symbols"] == ["BTC"]
    assert records[0].symbol == "BTC"
