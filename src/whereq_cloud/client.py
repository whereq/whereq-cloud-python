"""whereq.cloud — official Python SDK for the WhereQ data cloud.

A thin, typed-ish wrapper over the versioned ``/v1`` HTTP API at ``api.whereq.cloud``.
Public endpoints work with no key; metered endpoints take a ``X-API-Key``.

    from whereq_cloud import Client

    wq = Client()                               # public access
    wq = Client(api_key="wq_live_…")            # metered tier

    wq.cost_of_living("us:California,ca:Ontario")
    wq.prices(domain="rent", region="us", bedrooms=2)
    wq.get("/v1/trending", limit=10)            # escape hatch for any endpoint
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

__version__ = "0.1.0"
DEFAULT_BASE_URL = "https://api.whereq.cloud"


class WhereqError(Exception):
    """Raised on a non-2xx API response."""

    def __init__(self, status: int, message: str, url: str) -> None:
        self.status = status
        self.url = url
        self.message = message
        super().__init__(f"whereq.cloud API error {status} for {url}: {message}")


class Client:
    """Synchronous client for the whereq.cloud Data API.

    Args:
        api_key: optional ``wq_live_…`` key for metered endpoints (sent as ``X-API-Key``).
        base_url: override the API base (default ``https://api.whereq.cloud``).
        timeout: per-request timeout in seconds.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL,
                 timeout: float = 30.0) -> None:
        headers = {"Accept": "application/json",
                   "User-Agent": f"whereq.cloud-python/{__version__}"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._http = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout)

    # -- lifecycle -----------------------------------------------------------
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # -- core ----------------------------------------------------------------
    def get(self, path: str, **params: Any) -> Any:
        """GET any endpoint. ``None`` params are dropped. Returns parsed JSON."""
        clean = {k: v for k, v in params.items() if v is not None}
        r = self._http.get(path, params=clean)
        if r.status_code >= 400:
            try:
                msg = r.json().get("detail") or r.text
            except Exception:  # noqa: BLE001
                msg = r.text
            raise WhereqError(r.status_code, msg, str(r.url))
        return r.json()

    def get_text(self, path: str, **params: Any) -> str:
        """GET a non-JSON endpoint (e.g. CSV export) as text."""
        clean = {k: v for k, v in params.items() if v is not None}
        r = self._http.get(path, params=clean)
        if r.status_code >= 400:
            raise WhereqError(r.status_code, r.text, str(r.url))
        return r.text

    # -- prices / cost of living --------------------------------------------
    def prices(self, domain: Optional[str] = None, region: Optional[str] = None,
               bedrooms: Optional[int] = None, q: Optional[str] = None,
               limit: int = 60, offset: int = 0) -> Any:
        """Cost-of-living price series (fuel | food | energy | housing | rent)."""
        return self.get("/v1/prices", domain=domain, region=region, bedrooms=bedrooms,
                        q=q, limit=limit, offset=offset)

    def price(self, series_id: int) -> Any:
        """One price series with its full history."""
        return self.get(f"/v1/prices/{series_id}")

    def prices_csv(self, domain: Optional[str] = None, region: Optional[str] = None,
                   bedrooms: Optional[int] = None, q: Optional[str] = None) -> str:
        """Bulk CSV export of matching price series."""
        return self.get_text("/v1/prices/export", domain=domain, region=region,
                             bedrooms=bedrooms, q=q)

    def cost_of_living(self, places: str) -> Any:
        """Compare cost of living across US states / CA provinces / metros.

        ``places``: comma-separated ``region:name`` or ``m:<rent-series-id>``,
        e.g. ``"us:California,ca:Ontario,m:3958"``.
        """
        return self.get("/v1/cost-of-living", places=places)

    # -- discovery / facets --------------------------------------------------
    def catalog(self) -> Any:
        return self.get("/v1/catalog")

    def categories(self) -> Any:
        return self.get("/v1/categories")

    def regions(self) -> Any:
        return self.get("/v1/regions")

    def domains(self) -> Any:
        return self.get("/v1/domains")

    def trending(self, **params: Any) -> Any:
        return self.get("/v1/trending", **params)

    # -- finance -------------------------------------------------------------
    def hotstocks(self, limit: int = 20) -> Any:
        return self.get("/v1/hotstocks", limit=limit)

    def quotes(self, **params: Any) -> Any:
        return self.get("/v1/quotes", **params)

    def news(self, **params: Any) -> Any:
        return self.get("/v1/news", **params)

    def screener(self, **params: Any) -> Any:
        return self.get("/v1/screener", **params)

    def search(self, q: str, **params: Any) -> Any:
        return self.get("/v1/search", q=q, **params)

    # -- autos ---------------------------------------------------------------
    def autos_recalls(self, **params: Any) -> Any:
        return self.get("/v1/autos/recalls", **params)

    def autos_listings(self, **params: Any) -> Any:
        return self.get("/v1/autos/listings", **params)

    def autos_fuel_economy(self, **params: Any) -> Any:
        return self.get("/v1/autos/fuel-economy", **params)

    def autos_models(self, **params: Any) -> Any:
        return self.get("/v1/autos/models", **params)
