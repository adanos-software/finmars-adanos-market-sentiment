from __future__ import annotations

from finmars_adanos_connector.models import FinmarsUniversalRequest, SentimentImportRequest, SentimentRecord, Source
from finmars_adanos_connector.transform import records_to_simple_import_items, universal_to_import_request


def test_records_to_simple_import_items_preserves_requested_order() -> None:
    request = SentimentImportRequest(symbols=["NVDA", "TSLA"], source=Source.NEWS_STOCKS)
    records = [
        SentimentRecord(symbol="TSLA", sentiment_score=0.4, buzz_score=80, mentions=10),
        SentimentRecord(symbol="NVDA", sentiment_score=0.7, buzz_score=90, mentions=20),
    ]

    items = records_to_simple_import_items(request=request, records=records)

    assert [item["Instrument"] for item in items] == ["NVDA", "TSLA"]
    assert items[0]["Adanos Sentiment Score"] == 0.7
    assert items[1]["Adanos Buzz Score"] == 80


def test_records_to_simple_import_items_can_include_empty_rows() -> None:
    request = SentimentImportRequest(
        symbols=["TSLA", "AAPL"],
        source=Source.POLYMARKET_STOCKS,
        include_empty=True,
        instrument_column="Ticker",
        attribute_prefix="Adanos Polymarket",
    )

    items = records_to_simple_import_items(
        request=request,
        records=[SentimentRecord(symbol="TSLA", sentiment_score=0.4)],
    )

    assert len(items) == 2
    assert items[1]["Ticker"] == "AAPL"
    assert items[1]["Adanos Polymarket Sentiment Score"] is None
    assert items[1]["Adanos Polymarket Source"] == "polymarket_stocks"


def test_universal_to_import_request_reads_options() -> None:
    payload = FinmarsUniversalRequest(
        options={
            "tickers": "tsla; nvda, aapl",
            "adanos_source": "x_stocks",
            "adanos_days": "30",
            "include_empty": "false",
            "instrument_column": "Reference",
            "attribute_prefix": "Adanos X",
        }
    )

    request = universal_to_import_request(payload)

    assert request.symbols == ["TSLA", "NVDA", "AAPL"]
    assert request.source == Source.X_STOCKS
    assert request.days == 30
    assert request.include_empty is False
    assert request.instrument_column == "Reference"
    assert request.attribute_prefix == "Adanos X"


def test_universal_to_import_request_extracts_symbols_from_data_rows() -> None:
    payload = FinmarsUniversalRequest(
        options={"source": "reddit_stocks", "include_empty": "yes"},
        data=[
            {"Instrument": "tsla"},
            {"reference_for_pricing": "nvda"},
            {"ticker": "TSLA"},
        ],
    )

    request = universal_to_import_request(payload)

    assert request.symbols == ["TSLA", "NVDA"]
    assert request.include_empty is True
