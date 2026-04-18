# Finmars Setup Notes

This connector is designed for Finmars Universal Provider Data Procedures.

## Recommended Procedure

Create a Universal Provider procedure that posts to:

```text
https://your-connector-host.example/v1/finmars/universal/sentiment
```

If `FINMARS_CONNECTOR_TOKEN` is configured on the connector, add:

```text
X-Connector-Token: your-shared-secret
```

## Import Strategy

Use Simple Import mapping and persist the returned columns as instrument attributes or report custom fields:

```text
Instrument
Adanos Source
Adanos Sentiment Score
Adanos Buzz Score
Adanos Mentions
Adanos Trend
Adanos Bullish Percent
Adanos Bearish Percent
Adanos Observed At
```

The data is optional enrichment. Portfolios, trades, positions, prices, and accounting flows must continue to work without these fields.

## Suggested Attribute Types

| Column | Suggested type |
| --- | --- |
| `Adanos Sentiment Score` | number |
| `Adanos Buzz Score` | number |
| `Adanos Mentions` | integer |
| `Adanos Trend` | string |
| `Adanos Source` | string |
| `Adanos Bullish Percent` | number |
| `Adanos Bearish Percent` | number |
| `Adanos Observed At` | date/string |

## Operational Guidance

- Run the procedure on a schedule that matches the selected source. News/X can be more frequent than slow portfolio reporting workflows.
- Use `include_empty=true` when downstream reporting expects stable row counts.
- Use `attribute_prefix` to isolate multiple source mappings, for example `Adanos News` and `Adanos Polymarket`.
- Keep `ADANOS_API_KEY` and `ADANOS_BASE_URL` on the connector host. Finmars procedure options should only contain non-secret mapping settings.
