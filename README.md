# Adanos Market Sentiment Connector for Finmars

Optional Finmars Universal Provider connector for importing Adanos Market Sentiment API data into Finmars Simple Import workflows.

The connector is intentionally standalone. It does not patch Finmars Core, does not require Adanos data for normal Finmars usage, and keeps the Adanos API key on the connector side.

## What It Does

- Fetches watchlist sentiment from the Adanos `/compare` endpoints.
- Supports stocks from Reddit, X/Twitter, News, Polymarket, and crypto sentiment from Reddit.
- Converts Adanos responses into flat Simple Import rows for Finmars.
- Preserves Finmars instrument identifiers through a configurable instrument column.
- Batches large watchlists internally while respecting Adanos compare endpoint limits.

Adanos API reference: [https://api.adanos.org/docs/](https://api.adanos.org/docs/)

## Supported Sources

| Source | Adanos endpoint | Query key |
| --- | --- | --- |
| `reddit_stocks` | `/reddit/stocks/v1/compare` | `tickers` |
| `x_stocks` | `/x/stocks/v1/compare` | `tickers` |
| `news_stocks` | `/news/stocks/v1/compare` | `tickers` |
| `polymarket_stocks` | `/polymarket/stocks/v1/compare` | `tickers` |
| `reddit_crypto` | `/reddit/crypto/v1/compare` | `symbols` |

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
uvicorn finmars_adanos_connector.app:app --host 0.0.0.0 --port 8080
```

Minimum environment:

```bash
export ADANOS_API_KEY="sk_live_your_key_here"
export FINMARS_CONNECTOR_TOKEN="replace-with-a-random-shared-secret"
```

`FINMARS_CONNECTOR_TOKEN` is optional, but recommended. When configured, every connector request must include `X-Connector-Token`.

## Run With Docker

```bash
docker build -t finmars-adanos-market-sentiment .
docker run --rm -p 8080:8080 \
  -e ADANOS_API_KEY="sk_live_your_key_here" \
  -e FINMARS_CONNECTOR_TOKEN="replace-with-a-random-shared-secret" \
  finmars-adanos-market-sentiment
```

## Direct Simple Import Endpoint

```bash
curl -X POST http://localhost:8080/v1/finmars/simple-import/sentiment \
  -H "Content-Type: application/json" \
  -H "X-Connector-Token: replace-with-a-random-shared-secret" \
  -d @examples/simple_import_request.json
```

Response shape:

```json
{
  "source": "news_stocks",
  "count": 3,
  "data": [
    {
      "Instrument": "TSLA",
      "Adanos Source": "news_stocks",
      "Adanos Sentiment Score": 0.42,
      "Adanos Buzz Score": 71.5,
      "Adanos Mentions": 128,
      "Adanos Trend": "rising",
      "Adanos Bullish Percent": 63.0,
      "Adanos Bearish Percent": 22.0,
      "Adanos Observed At": "2026-04-18"
    }
  ]
}
```

## Finmars Universal Provider Endpoint

Configure a Finmars Universal Provider Data Procedure to call:

```text
POST https://your-connector-host.example/v1/finmars/universal/sentiment
```

Use the same `X-Connector-Token` header if `FINMARS_CONNECTOR_TOKEN` is set.

The connector accepts symbols either from `options.symbols`, `options.tickers`, `options.instruments`, or from incoming `data` rows using one of these fields:

```text
symbol, ticker, Instrument, instrument, reference_for_pricing, user_code
```

Recommended options:

```json
{
  "symbols": "TSLA,NVDA,AAPL",
  "adanos_source": "news_stocks",
  "adanos_days": 7,
  "include_empty": true,
  "instrument_column": "Instrument",
  "attribute_prefix": "Adanos"
}
```

The connector returns a Finmars-compatible envelope with `data` set to the Simple Import rows.

## Finmars Mapping

Recommended first integration target:

1. Create Generic Attributes on Finmars instruments for the Adanos columns you want to retain.
2. Run the Universal Provider Data Procedure on a scheduled basis.
3. Map `Instrument` to the Finmars instrument identifier used by your setup.
4. Map the `Adanos ...` columns to Generic Attributes or Balance Report custom fields.

Do not import sentiment values as price history. Sentiment, buzz, and source metadata are attributes/signals, not market prices.

## Request Options

| Option | Default | Description |
| --- | --- | --- |
| `symbols` / `tickers` / `instruments` | required unless symbols are in `data` | Comma-separated string or list. |
| `source` / `adanos_source` | `reddit_stocks` | One of the supported sources. |
| `days` / `adanos_days` | `7` | Lookback window, 1 to 365 days. |
| `include_empty` | `false` | Include rows with null Adanos fields when a symbol has no current data. |
| `instrument_column` | `Instrument` | Output column containing the Finmars instrument identifier. |
| `attribute_prefix` | `Adanos` | Prefix for generated output columns. |

## Development

```bash
pip install -e ".[test]"
python -m pytest -q
python -m compileall src
```

## Security Notes

- Configure `ADANOS_API_KEY` and `ADANOS_BASE_URL` server-side. The connector does not accept per-request API key or base URL overrides.
- Set `FINMARS_CONNECTOR_TOKEN` for shared-secret protection between Finmars and the connector.
- Terminate TLS at your ingress or reverse proxy if the connector is not running inside a private network.
- Treat Finmars Universal Provider options as non-secret configuration. Do not store Adanos API keys there.
