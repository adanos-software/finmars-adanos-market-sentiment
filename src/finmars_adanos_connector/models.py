from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Source(StrEnum):
    REDDIT_STOCKS = "reddit_stocks"
    X_STOCKS = "x_stocks"
    NEWS_STOCKS = "news_stocks"
    POLYMARKET_STOCKS = "polymarket_stocks"
    REDDIT_CRYPTO = "reddit_crypto"


class SentimentImportRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=500)
    source: Source = Source.REDDIT_STOCKS
    days: int = Field(default=7, ge=1, le=365)
    include_empty: bool = False
    instrument_column: str = Field(default="Instrument", min_length=1, max_length=80)
    attribute_prefix: str = Field(default="Adanos", min_length=1, max_length=80)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, symbols: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            value = str(symbol).strip().upper()
            if not value:
                continue
            if value not in seen:
                cleaned.append(value)
                seen.add(value)
        if not cleaned:
            raise ValueError("at least one non-empty symbol is required")
        return cleaned


class FinmarsUniversalRequest(BaseModel):
    id: int | str | None = None
    user: dict[str, Any] | None = None
    provider: str | None = None
    scheme_name: str | None = None
    scheme_type: str | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    date_from: str | None = None
    date_to: str | None = None
    error_status: int | None = None
    error_message: str | None = None


class SentimentRecord(BaseModel):
    symbol: str
    sentiment_score: float | None = None
    buzz_score: float | None = None
    mentions: int | None = None
    trend: str | None = None
    bullish_pct: float | None = None
    bearish_pct: float | None = None
    observed_at: str | None = None


class SimpleImportResponse(BaseModel):
    source: Source
    count: int
    data: list[dict[str, Any]]


class UniversalProviderResponse(BaseModel):
    id: int | str | None = None
    user: dict[str, Any] | None = None
    provider: Literal["adanos"] = "adanos"
    scheme_name: str | None = None
    scheme_type: str | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    error_status: int = 0
    error_message: str = ""
