"""whereq.cloud — official Python SDK for the WhereQ data cloud.

A thin, typed-ish wrapper over the versioned ``/v1`` HTTP API at ``api.whereq.cloud``.
Public endpoints work with no key; metered endpoints take a ``X-API-Key``.

    from whereq_cloud import Client

    wq = Client()                               # public access
    wq = Client(api_key="wq_live_…")            # metered tier

    wq.cost_of_living("us:California,ca:Ontario")
    wq.prices(domain="rent", region="us", bedrooms=2)
    wq.fuel_stations(country="CA", state="ON")   # station-level prices
    wq.get("/v1/trending", limit=10)            # escape hatch for any endpoint
"""
from __future__ import annotations

import os
from typing import Any, Iterator, Optional

import httpx

from whereq_cloud.types import (
    FUEL_COUNTRIES,
    FUEL_CURRENCIES,
    FUEL_PRODUCTS,
    CostOfLivingResponse,
    FuelStation,
    FuelStationDetail,
    FuelStationsResponse,
    GeoAtResponse,
    GeoBoundary,
    GeoConceptList,
    GeoOverlapList,
    GeoPlaceDetail,
    GeoPlaceList,
    LocalContentDetail,
    LocalContentList,
    LocalPlaceDetail,
    LocalPlaceList,
    LocalSourceList,
    LocalTaxonomy,
    PriceSeriesResponse,
    SchoolBoardList,
    SchoolBoundary,
    SchoolDetail,
    SchoolList,
    SchoolScores,
    SchoolTaxonomy,
    CatchmentList,
)

__version__ = "0.7.0"
DEFAULT_BASE_URL = "https://api.whereq.cloud"

#: Re-exported so callers can validate a filter before spending a request.
__all__ = [
    "Client",
    "WhereqError",
    "DEFAULT_BASE_URL",
    "FUEL_PRODUCTS",
    "FUEL_COUNTRIES",
    "FUEL_CURRENCIES",
    "__version__",
]


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
        # The key may come from the argument or the environment, in that order.
        key = api_key if api_key is not None else os.getenv("WHEREQ_API_KEY", "")
        headers = {"Accept": "application/json",
                   "User-Agent": f"whereq.cloud-python/{__version__}"}
        if key:
            headers["X-API-Key"] = key
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
               geo: Optional[str] = None, bedrooms: Optional[int] = None,
               q: Optional[str] = None, limit: int = 60, offset: int = 0) -> PriceSeriesResponse:
        """Cost-of-living price series (fuel | food | energy | housing | rent).

        ``region`` takes a region slug or a comma-separated list of them
        (``"us,ca"``); ``geo`` is a free-text place name ("Calgary, Alberta").
        """
        return self.get("/v1/prices", domain=domain, region=region, geo=geo,
                        bedrooms=bedrooms, q=q, limit=limit, offset=offset)

    def price(self, series_id: int) -> Any:
        """One price series with its full history."""
        return self.get(f"/v1/prices/{series_id}")

    def prices_csv(self, domain: Optional[str] = None, region: Optional[str] = None,
                   geo: Optional[str] = None, bedrooms: Optional[int] = None,
                   q: Optional[str] = None) -> str:
        """Bulk CSV export of matching price series."""
        return self.get_text("/v1/prices/export", domain=domain, region=region,
                             geo=geo, bedrooms=bedrooms, q=q)

    def cost_of_living(self, places: str) -> CostOfLivingResponse:
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

    # -- lottery --------------------------------------------------------------
    def lottery_draws(self, game: Optional[str] = None, days: int = 30,
                      limit: int = 50) -> Any:
        """Recent lottery draws, newest first.

        Args:
            game: a game slug, e.g. ``"powerball"``.
            days: how far back to look (1–730). Ignored on the preview.
            limit: 1–200 draws per page.

        Unentitled callers get the oldest 100 draws instead of the recent
        ones — check ``response["demo"]``.
        """
        return self.get("/v1/lottery/draws", game=game, days=days, limit=limit)

    def lottery_latest_draw(self, game: str) -> Any:
        """The most recent draw for a game.

        On the unentitled preview this is the *oldest* draw — the recent one
        is the gated, valuable row.
        """
        return self.get(f"/v1/lottery/draws/{game}/latest")

    def lottery_frequency(self, game: str, days: int = 365) -> Any:
        """Per-number frequency for a game over a window (30–1825 days)."""
        return self.get(f"/v1/lottery/draws/{game}/frequency", days=days)

    def lottery_games(self, country: Optional[str] = None,
                      region: Optional[str] = None) -> Any:
        """The lottery game registry: names, play rules and draw days."""
        return self.get("/v1/lottery/games", country=country, region=region)

    def lottery_game(self, slug: str) -> Any:
        """One game's full play rules and metadata."""
        return self.get(f"/v1/lottery/games/{slug}")

    # -- fuel (gas & diesel) -------------------------------------------------
    def fuel_stations(self, country: Optional[str] = None, state: Optional[str] = None,
                      municipality: Optional[str] = None, product: Optional[str] = None,
                      bbox: Optional[str] = None, q: Optional[str] = None,
                      limit: int = 100, offset: int = 0,
                      **extra: Any) -> FuelStationsResponse:
        """Geolocated retail fuel stations with their latest prices.

        Coverage: Mexico (``MX``, CRE open data), the United States (``US``)
        and Canada (``CA``). Prices are in **local currency per litre** —
        ``MXN/L``, ``USD/L`` and ``CAD/L`` respectively.

        Args:
            country: ``"MX"``, ``"US"`` or ``"CA"``.
            state: state/province name *or* ISO code — ``"Ontario"`` and
                ``"ON"`` both work for Canada, ``"Texas"``/``"TX"`` for the US.
            municipality: city name, e.g. ``"Mississauga"``.
            product: one of ``regular``, ``midgrade``, ``premium``, ``diesel``.
            bbox: ``"minLon,minLat,maxLon,maxLat"`` for a map viewport.
            q: station-name search.
            limit: 1–500 rows per page (default 100).
            offset: row offset for paging.
            **extra: any other query parameter the API accepts.

        Unentitled callers get a 100-row preview of the oldest rows and the
        pagination arguments are ignored — check ``response["demo"]``.
        """
        return self.get("/v1/fuel/stations", country=country, state=state,
                        municipality=municipality, product=product, bbox=bbox,
                        q=q, limit=limit, offset=offset, **extra)

    def fuel_station(self, station_id: Any, product: Optional[str] = None,
                     days: int = 90) -> FuelStationDetail:
        """One station: location, latest prices and its price-change timeline.

        Args:
            station_id: the station's numeric id.
            product: restrict the timeline to one product.
            days: how far back the timeline reaches (1–1825, default 90).
        """
        return self.get(f"/v1/fuel/stations/{station_id}", product=product, days=days)

    def iter_fuel_stations(self, page_size: int = 500, **filters: Any) -> Iterator[FuelStation]:
        """Yield every matching station, paging through the API for you.

        Only meaningful with an entitled key. The unentitled preview always
        returns the *same* oldest 100 rows and ignores the paging arguments,
        so there is nothing more to fetch: this yields that first page and
        stops rather than looping on it.
        """
        offset = 0
        while True:
            page = self.fuel_stations(limit=page_size, offset=offset, **filters)
            stations = page.get("stations") or []
            if not stations:
                return
            yield from stations
            if page.get("demo"):
                return                      # preview: every page is the same slice
            offset += len(stations)
            total = page.get("total")
            if total is not None and offset >= total:
                return

    def fuel_prices(self, region: Optional[str] = None, geo: Optional[str] = None,
                    q: Optional[str] = None, limit: int = 60,
                    offset: int = 0) -> PriceSeriesResponse:
        """Aggregated fuel price series (state / national / metro).

        These are the *series* behind the charts — EIA weekly for the US,
        StatCan monthly for Canada, CRE for Mexico — not the station-level
        prices that ``fuel_stations()`` returns.
        """
        return self.get("/v1/prices", domain="fuel", region=region, geo=geo,
                        q=q, limit=limit, offset=offset)

    # -- geography (places, boundaries, hierarchy) ---------------------------
    def geo_places(self, kind: Optional[str] = None, source: Optional[str] = None,
                   country: Optional[str] = None, q: Optional[str] = None,
                   bbox: Optional[str] = None, has_boundary: Optional[bool] = None,
                   limit: int = 50, offset: int = 0) -> GeoPlaceList:
        """The place list — provinces, regions, municipalities, cities, towns,
        wards, neighbourhoods, countries.

        Args:
            kind: one concept — ``country``, ``province``, ``region``,
                ``municipality``, ``city``, ``town``, ``ward``,
                ``neighbourhood``…
            source: ``"osm"`` (the concept layer) or ``"geoboundaries"``
                (the formal layer). Both are kept; they overlap.
            country: ISO country code. Either spelling works — ``"CA"``
                and ``"CAN"`` find the same places, in both vocabularies.
            q: name search.
            bbox: ``"minLon,minLat,maxLon,maxLat"``.
            has_boundary: only places with a drawable outline.
            limit: 1–200 rows per page.
            offset: row offset for paging.
        """
        return self.get("/v1/geo/places", kind=kind, source=source,
                        country=country, q=q, bbox=bbox,
                        has_boundary=has_boundary, limit=limit, offset=offset)

    def geo_place(self, uid: str) -> GeoPlaceDetail:
        """One place, with its containers AND the places inside it.

        The parents are a list on purpose: a place belongs to several
        things at once.
        """
        return self.get(f"/v1/geo/places/{uid}")

    def geo_boundary(self, uid: str, simplify: Optional[int] = None) -> GeoBoundary:
        """A place's outline as GeoJSON.

        ``simplify`` is in METRES: the outline keeps every corner more
        than that far from the original, and the result is still a valid
        polygon.
        """
        return self.get(f"/v1/geo/places/{uid}/boundary", simplify=simplify)

    def geo_at(self, lon: float, lat: float) -> GeoAtResponse:
        """Every place containing a point, broadest first.

        The answer to "which district is this?" without picking a winner:
        a point downtown Toronto lands in a neighbourhood, a ward, a
        city, a census division, a province and a country, and all of
        them are returned.
        """
        return self.get("/v1/geo/at", lon=lon, lat=lat)

    def geo_concepts(self) -> GeoConceptList:
        """The vocabulary: every concept, in both languages, with a live
        count of how many places and outlines it has."""
        return self.get("/v1/geo/concepts")

    def geo_overlaps(self, bbox: str, min_ratio: Optional[float] = None,
                     limit: Optional[int] = None) -> GeoOverlapList:
        """The places of different kinds that cover the same ground.

        Args:
            bbox: ``"minLon,minLat,maxLon,maxLat"`` — required. Comparing
                every pair in the country is a quadratic join, and nobody
                asks that question about all of Canada at once.
            min_ratio: the smallest overlap worth reporting.
            limit: how many pairs to return.
        """
        return self.get("/v1/geo/overlaps", bbox=bbox, min_ratio=min_ratio,
                        limit=limit)

    # -- local (news, events, stories, places) ------------------------------
    def local_content(self, type: Optional[str] = None, category: Optional[str] = None,
                      source: Optional[str] = None, city: Optional[str] = None,
                      province: Optional[str] = None, bbox: Optional[str] = None,
                      q: Optional[str] = None, since: Optional[str] = None,
                      until: Optional[str] = None,
                      has_location: Optional[bool] = None,
                      include_expired: bool = False,
                      limit: int = 50, cursor: Optional[str] = None) -> LocalContentList:
        """The local feed — news, events, stories and notices.

        Args:
            type: ``news``, ``event``, ``story``…
            category: the feed's own category.
            source: the feed's slug.
            city / province: where it happened.
            bbox: ``"minLon,minLat,maxLon,maxLat"``.
            q: free text.
            since / until: ISO timestamps.
            has_location: only items with a position.
            include_expired: expired content is filtered out by default.
            limit: rows per page.
            cursor: the next page's cursor.
        """
        return self.get("/v1/local/content", type=type, category=category,
                        source=source, city=city, province=province, bbox=bbox,
                        q=q, since=since, until=until,
                        has_location=has_location,
                        include_expired=include_expired, limit=limit, cursor=cursor)

    def local_content_item(self, content_id: int) -> LocalContentDetail:
        """One item, with its tags."""
        return self.get(f"/v1/local/content/{content_id}")

    def local_places(self, category: Optional[str] = None, kind: Optional[str] = None,
                     sub: Optional[str] = None, bbox: Optional[str] = None,
                     lat: Optional[float] = None, lng: Optional[float] = None,
                     radius_km: Optional[float] = None, q: Optional[str] = None,
                     limit: int = 50, offset: int = 0) -> LocalPlaceList:
        """The points of interest — the OpenStreetMap sweep.

        Args:
            category: the POI category.
            kind: the POI kind.
            sub: a sub-category.
            bbox: ``"minLon,minLat,maxLon,maxLat"``.
            lat / lng / radius_km: a proximity search — give all three.
            q: free text.
            limit / offset: paging.
        """
        return self.get("/v1/local/places", category=category, kind=kind,
                        sub=sub, bbox=bbox, lat=lat, lng=lng,
                        radius_km=radius_km, q=q, limit=limit, offset=offset)

    def local_place(self, place_id: int) -> LocalPlaceDetail:
        """One place."""
        return self.get(f"/v1/local/places/{place_id}")

    def local_sources(self, enabled: Optional[bool] = None,
                      kind: Optional[str] = None,
                      limit: int = 100) -> LocalSourceList:
        """The configured local feeds."""
        return self.get("/v1/local/sources", enabled=enabled, kind=kind, limit=limit)

    def local_taxonomy(self) -> LocalTaxonomy:
        """The local vocabulary — types, categories, place categories, sources."""
        return self.get("/v1/local/taxonomy")

    # -- schools -------------------------------------------------------------
    def schools(self, q: Optional[str] = None, board: Optional[str] = None,
                city: Optional[str] = None, province: Optional[str] = None,
                type: Optional[str] = None, bbox: Optional[str] = None,
                lat: Optional[float] = None, lng: Optional[float] = None,
                radius_km: Optional[float] = None,
                has_boundary: Optional[bool] = None,
                limit: int = 50, offset: int = 0) -> SchoolList:
        """The school directory.

        Args:
            q: name or city search.
            board: the board's slug (``ycdsb``, ``tdsb``…).
            city / province: where the school is.
            type: ``elementary``, ``secondary``, ``combined`` or ``other``.
            bbox: ``"minLon,minLat,maxLon,maxLat"``.
            lat / lng / radius_km: a proximity search — give all three.
            has_boundary: only schools that have (or do not have) a catchment.
            limit / offset: paging.
        """
        return self.get("/v1/schools", q=q, board=board, city=city,
                        province=province, type=type, bbox=bbox,
                        lat=lat, lng=lng, radius_km=radius_km,
                        has_boundary=has_boundary, limit=limit, offset=offset)

    def school_boards(self) -> SchoolBoardList:
        """The board registry — the vocabulary the ``board`` filter uses."""
        return self.get("/v1/schools/boards")

    def school_taxonomy(self) -> SchoolTaxonomy:
        """The school vocabulary and the headline counts."""
        return self.get("/v1/schools/taxonomy")

    def schools_at(self, lat: float, lng: float, limit: int = 20) -> CatchmentList:
        """The catchments that cover a point.

        **Licensed.** This reads the catchment polygons, so it needs the
        ``school_licensed`` scope — a key without it gets a 403.
        """
        return self.get("/v1/schools/at", lat=lat, lng=lng, limit=limit)

    def school(self, uid: str) -> SchoolDetail:
        """One school.

        The uid is board-qualified — ``ycdsb/0158``, or
        ``ycdsb/st-theresa-of-lisieux-chs`` when the board publishes no
        code. It carries a slash, and the API's route is built for that.

        The scores come back only with the ``school_licensed`` scope.
        """
        return self.get(f"/v1/schools/{uid}")

    def school_boundary(self, uid: str,
                        simplify: Optional[int] = None) -> SchoolBoundary:
        """A school's catchment outline, as GeoJSON.

        **Licensed.** ``simplify`` is in METRES.
        """
        return self.get(f"/v1/schools/{uid}/boundary", simplify=simplify)

    def school_scores(self, uid: str, year: Optional[int] = None) -> SchoolScores:
        """One year's assessment snapshot, with the EQAO marks.

        **Licensed.** ``year`` picks a year; the latest is the default.
        """
        return self.get(f"/v1/schools/{uid}/scores", year=year)

