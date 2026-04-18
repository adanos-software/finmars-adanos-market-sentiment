from __future__ import annotations

from typing import Any

from finmars_adanos_connector.adanos import normalize_symbol
from finmars_adanos_connector.models import FinmarsUniversalRequest, SentimentImportRequest, SentimentRecord, Source


DEFAULT_SYMBOL_FIELDS = (
    "symbol",
    "ticker",
    "Instrument",
    "instrument",
    "reference_for_pricing",
    "user_code",
)


def records_to_simple_import_items(
    *,
    request: SentimentImportRequest,
    records: list[SentimentRecord],
) -> list[dict[str, Any]]:
    by_symbol = {record.symbol: record for record in records}
    items: list[dict[str, Any]] = []

    for symbol in request.symbols:
        lookup_symbol = normalize_symbol(symbol, source=request.source)
        record = by_symbol.get(lookup_symbol)
        if record is None and not request.include_empty:
            continue

        items.append(
            _record_to_item(
                symbol=lookup_symbol,
                source=request.source,
                record=record,
                instrument_column=request.instrument_column,
                prefix=request.attribute_prefix,
            )
        )

    return items


def universal_to_import_request(payload: FinmarsUniversalRequest) -> SentimentImportRequest:
    options = payload.options or {}
    source = Source(str(options.get("source") or options.get("adanos_source") or Source.REDDIT_STOCKS))
    symbols = _extract_symbols(options=options, data=payload.data)

    return SentimentImportRequest(
        symbols=symbols,
        source=source,
        days=int(options.get("days") or options.get("adanos_days") or 7),
        include_empty=_coerce_bool(options.get("include_empty", False)),
        instrument_column=str(options.get("instrument_column") or "Instrument"),
        attribute_prefix=str(options.get("attribute_prefix") or "Adanos"),
    )


def _record_to_item(
    *,
    symbol: str,
    source: Source,
    record: SentimentRecord | None,
    instrument_column: str,
    prefix: str,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        instrument_column: symbol,
        f"{prefix} Source": source.value,
    }

    if record is None:
        item.update(
            {
                f"{prefix} Sentiment Score": None,
                f"{prefix} Buzz Score": None,
                f"{prefix} Mentions": None,
                f"{prefix} Trend": None,
                f"{prefix} Bullish Percent": None,
                f"{prefix} Bearish Percent": None,
                f"{prefix} Observed At": None,
            }
        )
        return item

    item.update(
        {
            f"{prefix} Sentiment Score": record.sentiment_score,
            f"{prefix} Buzz Score": record.buzz_score,
            f"{prefix} Mentions": record.mentions,
            f"{prefix} Trend": record.trend,
            f"{prefix} Bullish Percent": record.bullish_pct,
            f"{prefix} Bearish Percent": record.bearish_pct,
            f"{prefix} Observed At": record.observed_at,
        }
    )
    return item


def _extract_symbols(*, options: dict[str, Any], data: list[dict[str, Any]]) -> list[str]:
    for key in ("symbols", "tickers", "instruments"):
        symbols = _coerce_symbols(options.get(key))
        if symbols:
            return symbols

    symbols = []
    seen = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        for key in DEFAULT_SYMBOL_FIELDS:
            value = row.get(key)
            if value is None:
                continue
            symbol = str(value).strip().upper()
            if symbol and symbol not in seen:
                symbols.append(symbol)
                seen.add(symbol)
                break

    if not symbols:
        raise ValueError("No symbols found in Finmars options or data rows")
    return symbols


def _coerce_symbols(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_symbols = value.replace(";", ",").split(",")
    elif isinstance(value, list | tuple | set):
        raw_symbols = list(value)
    else:
        raw_symbols = [value]

    symbols: list[str] = []
    seen: set[str] = set()
    for raw_symbol in raw_symbols:
        symbol = str(raw_symbol).strip().upper()
        if symbol and symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)
    return symbols


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
