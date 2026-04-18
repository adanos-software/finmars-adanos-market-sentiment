from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from finmars_adanos_connector.models import SentimentRecord, Source


SOURCE_ENDPOINTS: dict[Source, tuple[str, str]] = {
    Source.REDDIT_STOCKS: ("/reddit/stocks/v1/compare", "tickers"),
    Source.X_STOCKS: ("/x/stocks/v1/compare", "tickers"),
    Source.NEWS_STOCKS: ("/news/stocks/v1/compare", "tickers"),
    Source.POLYMARKET_STOCKS: ("/polymarket/stocks/v1/compare", "tickers"),
    Source.REDDIT_CRYPTO: ("/reddit/crypto/v1/compare", "symbols"),
}

MAX_COMPARE_SYMBOLS_PER_REQUEST = 10
SYMBOL_KEYS = ("symbol", "ticker", "token", "asset", "instrument")
SENTIMENT_KEYS = ("sentiment_score", "sentiment", "score", "adanos_sentiment_score")
BUZZ_KEYS = ("buzz_score", "buzz", "adanos_buzz_score")
MENTION_KEYS = ("mentions", "mention_count", "total_mentions", "trade_count", "count")
BULLISH_KEYS = ("bullish_pct", "bullish_percent", "positive_pct")
BEARISH_KEYS = ("bearish_pct", "bearish_percent", "negative_pct")
OBSERVED_KEYS = ("observed_at", "updated_at", "date", "as_of")


class AdanosClientError(RuntimeError):
    pass


class AdanosClient:
    def __init__(self, *, timeout: float = 20.0) -> None:
        self._timeout = timeout

    async def fetch_compare(
        self,
        *,
        symbols: list[str],
        source: Source,
        days: int,
        api_key: str,
        base_url: str,
    ) -> list[SentimentRecord]:
        path, query_key = SOURCE_ENDPOINTS[source]
        headers = {"X-API-Key": api_key}
        records: list[SentimentRecord] = []

        try:
            async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=self._timeout) as client:
                for chunk in _chunks(symbols, MAX_COMPARE_SYMBOLS_PER_REQUEST):
                    params: dict[str, str | int] = {query_key: ",".join(chunk), "days": days}
                    response = await client.get(path, params=params, headers=headers)
                    response.raise_for_status()
                    records.extend(normalize_records(response.json(), source=source))
        except httpx.HTTPStatusError as exc:
            raise AdanosClientError(f"Adanos API returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise AdanosClientError(f"Adanos API request failed: {exc.__class__.__name__}") from exc

        return records


def normalize_records(payload: Any, *, source: Source) -> list[SentimentRecord]:
    rows = _extract_rows(payload)
    records: list[SentimentRecord] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = _first_text(row, SYMBOL_KEYS)
        if not symbol:
            continue
        records.append(
            SentimentRecord(
                symbol=normalize_symbol(symbol, source=source),
                sentiment_score=_first_float(row, SENTIMENT_KEYS),
                buzz_score=_first_float(row, BUZZ_KEYS),
                mentions=_first_int(row, MENTION_KEYS),
                trend=_first_text(row, ("trend", "direction")),
                bullish_pct=_first_float(row, BULLISH_KEYS),
                bearish_pct=_first_float(row, BEARISH_KEYS),
                observed_at=_first_text(row, OBSERVED_KEYS),
            )
        )

    return records


def normalize_symbol(symbol: str, *, source: Source) -> str:
    normalized = symbol.strip().upper().lstrip("$")
    normalized = normalized.replace("_", "-")

    if source == Source.REDDIT_CRYPTO:
        for suffix in ("-USDT", "-USDC", "-USD", "/USDT", "/USDC", "/USD"):
            if normalized.endswith(suffix):
                return normalized[: -len(suffix)]
    return normalized


def _extract_rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for key in ("data", "results", "items", "stocks", "tokens", "symbols"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    keyed_rows = []
    for key, value in payload.items():
        if isinstance(value, dict):
            row = dict(value)
            row.setdefault("symbol", key)
            keyed_rows.append(row)
    return keyed_rows


def _chunks(symbols: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(symbols), size):
        yield symbols[index : index + size]


def _first_text(row: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_float(row: dict[str, Any], keys: Iterable[str]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_int(row: dict[str, Any], keys: Iterable[str]) -> int | None:
    value = _first_float(row, keys)
    if value is None:
        return None
    return int(value)
