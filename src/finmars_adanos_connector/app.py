from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from finmars_adanos_connector import __version__
from finmars_adanos_connector.adanos import AdanosClient, AdanosClientError
from finmars_adanos_connector.models import (
    FinmarsUniversalRequest,
    SentimentImportRequest,
    SimpleImportResponse,
    Source,
    UniversalProviderResponse,
)
from finmars_adanos_connector.settings import Settings, load_settings
from finmars_adanos_connector.transform import records_to_simple_import_items, universal_to_import_request


def get_settings() -> Settings:
    return load_settings()


def get_adanos_client(settings: Annotated[Settings, Depends(get_settings)]) -> AdanosClient:
    return AdanosClient(timeout=settings.request_timeout_seconds)


def verify_connector_token(
    settings: Annotated[Settings, Depends(get_settings)],
    x_connector_token: Annotated[str | None, Header(alias="X-Connector-Token")] = None,
) -> None:
    if settings.connector_token and not compare_digest(x_connector_token or "", settings.connector_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid connector token")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Adanos Market Sentiment Connector for Finmars",
        version=__version__,
        description="Optional Finmars Universal Provider connector for Adanos market sentiment data.",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "finmars-adanos-market-sentiment", "version": __version__}

    @app.get("/v1/sources")
    async def sources() -> dict[str, list[str]]:
        return {"sources": [source.value for source in Source]}

    @app.post("/v1/finmars/simple-import/sentiment", response_model=SimpleImportResponse)
    async def simple_import_sentiment(
        request: SentimentImportRequest,
        _: Annotated[None, Depends(verify_connector_token)],
        client: Annotated[AdanosClient, Depends(get_adanos_client)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> SimpleImportResponse:
        items = await fetch_simple_import_items(request=request, client=client, settings=settings)
        return SimpleImportResponse(source=request.source, count=len(items), data=items)

    @app.post("/v1/finmars/universal/sentiment", response_model=UniversalProviderResponse)
    async def finmars_universal_sentiment(
        request: FinmarsUniversalRequest,
        _: Annotated[None, Depends(verify_connector_token)],
        client: Annotated[AdanosClient, Depends(get_adanos_client)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> UniversalProviderResponse:
        try:
            import_request = universal_to_import_request(request)
            items = await fetch_simple_import_items(request=import_request, client=client, settings=settings)
        except Exception as exc:
            return UniversalProviderResponse(
                id=request.id,
                user=request.user,
                scheme_name=request.scheme_name,
                scheme_type=request.scheme_type,
                error_status=1,
                error_message=str(exc),
            )

        return UniversalProviderResponse(
            id=request.id,
            user=request.user,
            scheme_name=request.scheme_name,
            scheme_type=request.scheme_type,
            data=items,
        )

    return app


async def fetch_simple_import_items(
    *,
    request: SentimentImportRequest,
    client: AdanosClient,
    settings: Settings,
) -> list[dict]:
    api_key = _resolve_api_key(settings)

    try:
        records = await client.fetch_compare(
            symbols=request.symbols,
            source=request.source,
            days=request.days,
            api_key=api_key,
            base_url=settings.adanos_base_url,
        )
    except AdanosClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return records_to_simple_import_items(request=request, records=records)


def _resolve_api_key(settings: Settings) -> str:
    if settings.adanos_api_key:
        return settings.adanos_api_key
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="ADANOS_API_KEY is not configured",
    )


app = create_app()
