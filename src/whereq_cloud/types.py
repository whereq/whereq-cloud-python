"""Typed response shapes for the whereq.cloud API.

These mirror the JSON the API actually sends. They are documentation the type
checker can read — not a validation layer: the client returns whatever the
server sent, and these describe it.
"""
from __future__ import annotations

from typing import Optional, TypedDict

# -- fuel (station-level) -----------------------------------------------------

#: The products a station can quote. Mexico's CRE feed carries the first,
#: second and fourth; GasBuddy (US/Canada) adds midgrade.
FUEL_PRODUCTS = ("regular", "midgrade", "premium", "diesel")

#: Countries with station-level fuel data.
FUEL_COUNTRIES = ("MX", "US", "CA")

#: The unit each country quotes in — always local currency per litre.
FUEL_CURRENCIES = {"MX": "MXN/L", "US": "USD/L", "CA": "CAD/L"}


class FuelStationPrice(TypedDict):
    """One product's latest price at a station."""

    price: float
    observed_at: str


class FuelStationBase(TypedDict):
    """The station fields, without the prices.

    ``state`` is the human label ("Ontario", "Texas"); ``state_iso`` is the
    two-letter code ("ON", "TX") and matches Mexico's rows, which have the
    label only.
    """

    id: int
    source: str
    ext_id: str
    country: str
    name: str
    brand: Optional[str]
    state: Optional[str]
    state_iso: Optional[str]
    municipality: Optional[str]
    lat: Optional[float]
    lon: Optional[float]


class FuelStation(FuelStationBase):
    """A station as the *list* endpoint returns it — with its latest prices."""

    prices: dict[str, FuelStationPrice]


class FuelStationSummary(FuelStationBase, total=False):
    """A station as the *detail* endpoint returns it.

    No ``prices`` map: the timeline comes back as the separate ``prices``
    array on the response, one entry per price change.
    """


class _FuelStationsBase(TypedDict):
    """The part of the station-list envelope that is always present."""

    as_of: str
    count: int
    stations: list[FuelStation]


class FuelStationsResponse(_FuelStationsBase, total=False):
    """``GET /v1/fuel/stations``.

    Unentitled callers get a 100-row preview of the oldest rows: ``demo`` is
    ``True``, ``total`` is ``None`` and ``limit``/``offset`` are ignored.
    """

    demo: bool
    preview_rows: int
    note: str
    upgrade_url: str
    total: Optional[int]


class FuelStationPricePoint(TypedDict):
    """One observed price change — the intra-day timeline for a station."""

    product: str
    observed_at: str
    price: float


class _FuelStationDetailBase(TypedDict):
    station: FuelStationSummary
    prices: list[FuelStationPricePoint]


class FuelStationDetail(_FuelStationDetailBase, total=False):
    """``GET /v1/fuel/stations/{id}``.

    ``days`` is ``None`` in the unentitled preview.
    """

    demo: bool
    preview_rows: int
    note: str
    upgrade_url: str
    days: Optional[int]


# -- prices (aggregated series) ----------------------------------------------

class PriceSeries(TypedDict):
    """One aggregated price series (state / national / metro)."""

    id: int
    domain: str
    source: str
    region: Optional[str]
    geo: Optional[str]
    item: str
    item_cn: Optional[str]
    unit: Optional[str]
    unit_cn: Optional[str]
    frequency: Optional[str]
    latest_period: Optional[str]
    latest_value: Optional[float]
    prev_value: Optional[float]
    points: Optional[int]
    spark: list[float]


class PriceSeriesResponse(TypedDict):
    """``GET /v1/prices`` — a page of series plus the page's own metadata."""

    count: int
    domain: Optional[str]
    region: Optional[str]
    limit: int
    offset: int
    data: list[PriceSeries]


class CostOfLivingResponse(TypedDict, total=False):
    """``GET /v1/cost-of-living`` — a cross-region comparison."""

    places: list[dict]


# -- geography (places, boundaries, hierarchy) --------------------------------

class GeoPlace(TypedDict):
    """One place — a province, a municipality, a ward, a neighbourhood.

    ``kind`` is the platform's own concept (``province``, ``region``,
    ``municipality``, ``city``, ``town``, ``ward``, ``neighbourhood``…),
    not the source's admin level. ``country_code`` is the two-letter ISO
    code and is the same for both vocabularies — the API accepts
    ``CA`` or ``CAN`` in a country filter and answers with the same
    places either way.
    """

    uid: str
    kind: str
    kind_source: str
    name: str
    name_en: Optional[str]
    name_zh: Optional[str]
    name_local: Optional[str]
    official_name: Optional[str]
    source: str
    source_id: str
    source_url: Optional[str]
    license: Optional[str]
    raw_admin_level: Optional[int]
    raw_place: Optional[str]
    raw_boundary: Optional[str]
    country_code: Optional[str]
    province_code: Optional[str]
    iso_code: Optional[str]
    ref: Optional[str]
    population: Optional[int]
    population_date: Optional[str]
    wikidata: Optional[str]
    wikipedia: Optional[str]
    website: Optional[str]
    capital: Optional[str]
    centroid_lon: Optional[float]
    centroid_lat: Optional[float]
    bbox_min_lon: Optional[float]
    bbox_min_lat: Optional[float]
    bbox_max_lon: Optional[float]
    bbox_max_lat: Optional[float]
    area_km2: Optional[float]
    has_boundary: bool


class GeoPlaceList(TypedDict):
    """``GET /v1/geo/places`` — a page of places."""

    count: int
    data: list[GeoPlace]
    limit: int
    offset: int


class GeoParent(TypedDict):
    """One container of a place, as the detail endpoint lists them.

    A place has SEVERAL parents — a neighbourhood is in a ward, in a
    city, in a census division and in a province, all at once. The list
    is deliberately a list.
    """

    uid: str
    kind: str
    name: str
    source: str
    area_ratio: Optional[float]
    is_primary: bool


class GeoPlaceDetail(TypedDict):
    """``GET /v1/geo/places/{uid}`` — one place with its containers and
    the places inside it."""

    uid: str
    place: GeoPlace
    parents: list[GeoParent]
    children: list[GeoParent]


class GeoConcept(TypedDict):
    """One concept in the vocabulary, with a live count behind it."""

    kind: str
    name: str
    name_cn: Optional[str]
    description: Optional[str]
    description_cn: Optional[str]
    places: int
    with_boundary: int
    rank: int


class GeoConceptList(TypedDict):
    """``GET /v1/geo/concepts`` — the vocabulary, explained."""

    count: int
    concepts: list[GeoConcept]
    sources: list[dict]


class GeoOverlap(TypedDict):
    """Two places of DIFFERENT kinds covering the same ground.

    This is the deliberate part of the dataset: a census subdivision and
    an OpenStreetMap city boundary that describe the same town in two
    vocabularies. The platform keeps both rather than picking one.
    """

    a_id: int
    b_id: int
    a_uid: str
    b_uid: str
    a_name: str
    b_name: str
    a_kind: str
    b_kind: str
    a_source: str
    b_source: str
    overlap_ratio: float
    a_concept: str
    b_concept: str


class GeoOverlapList(TypedDict):
    """``GET /v1/geo/overlaps`` — the overlapping pairs inside a box."""

    bbox: dict
    min_ratio: float
    count: int
    overlaps: list[GeoOverlap]


class GeoAtPlace(TypedDict, total=False):
    """One place in the containing stack at a point.

    ``country_code`` is on every level, so the stack can be read without
    a second lookup.
    """

    uid: str
    kind: str
    kind_source: str
    name: str
    name_en: Optional[str]
    name_zh: Optional[str]
    source: str
    raw_admin_level: Optional[int]
    raw_place: Optional[str]
    population: Optional[int]
    wikidata: Optional[str]
    centroid_lon: Optional[float]
    centroid_lat: Optional[float]
    area_km2: Optional[float]
    country_code: Optional[str]
    province_code: Optional[str]
    boundary_area_km2: Optional[float]
    concept: dict


class GeoAtResponse(TypedDict):
    """``GET /v1/geo/at`` — every place containing a point.

    Broadest first: country, province, region, municipality, city, ward,
    neighbourhood. The answer to "where am I?" without pretending one of
    them is *the* answer.
    """

    lon: float
    lat: float
    count: int
    places: list[GeoAtPlace]


class GeoBoundary(TypedDict, total=False):
    """``GET /v1/geo/places/{uid}/boundary`` — the outline as GeoJSON.

    A ``FeatureCollection`` you can hand straight to a map library.
    """

    type: str
    features: list[dict]


# -- local (news, events, stories, places) -----------------------------------


class LocalContent(TypedDict, total=False):
    """One item from a local feed — a story, an event, a notice."""

    id: int
    type: str
    category: Optional[str]
    title: str
    summary: Optional[str]
    description: Optional[str]
    source_name: Optional[str]
    source_url: Optional[str]
    url: Optional[str]
    publish_time: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    geocode_status: Optional[str]
    confidence_score: Optional[float]
    status: str
    expires_at: Optional[str]
    tags: list[str]


class LocalContentList(TypedDict, total=False):
    """``GET /v1/local/content`` — the page envelope."""

    data: list[LocalContent]
    pagination: dict


class LocalContentDetail(LocalContent, total=False):
    """``GET /v1/local/content/{id}`` — one item, with its tags."""

    tags: list[str]


class LocalPlace(TypedDict, total=False):
    """One point of interest."""

    id: int
    source: str
    source_url: Optional[str]
    license: Optional[str]
    external_id: str
    name: str
    latitude: Optional[float]
    longitude: Optional[float]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    category: Optional[str]
    kind: Optional[str]
    metadata: dict


class LocalPlaceList(TypedDict, total=False):
    """``GET /v1/local/places`` — the page envelope."""

    data: list[LocalPlace]
    pagination: dict


class LocalPlaceDetail(LocalPlace, total=False):
    """``GET /v1/local/places/{id}`` — one place."""


class LocalSource(TypedDict, total=False):
    """One configured local feed."""

    slug: str
    name: str
    kind: str
    url: Optional[str]
    default_type: Optional[str]
    default_city: Optional[str]
    default_province: Optional[str]
    default_country: Optional[str]
    enabled: bool
    crawl_interval_minutes: int


class LocalSourceList(TypedDict, total=False):
    """``GET /v1/local/sources`` — the page envelope."""

    data: list[LocalSource]
    pagination: dict


class LocalTaxonomy(TypedDict, total=False):
    """``GET /v1/local/taxonomy`` — the vocabulary, in one call."""

    types: list[dict]
    categories: list[dict]
    place_categories: list[dict]
    sources: list[dict]


# -- schools -------------------------------------------------------------------


class SchoolBoard(TypedDict, total=False):
    """One school board."""

    slug: str
    name: str
    type: Optional[str]
    region: Optional[str]
    school_count: int


class SchoolSummary(TypedDict, total=False):
    """One school.

    The ``hs_*`` fields are **present only when the API key holds the
    ``school_licensed`` scope**. Without it they are absent — not null —
    so a caller can tell "you are not entitled to this" from "there is no
    value here".
    """

    uid: str
    name: str
    type: Optional[str]
    status: Optional[str]
    province: Optional[str]
    region: Optional[str]
    city: Optional[str]
    municipality: Optional[str]
    board: Optional[SchoolBoard]
    latitude: Optional[float]
    longitude: Optional[float]
    grade_range: Optional[str]
    programs: list[str]
    has_boundary: bool
    source: Optional[str]
    source_url: Optional[str]
    license: Optional[str]
    hs_score: Optional[float]
    hs_rank: Optional[int]
    hs_rank_total: Optional[int]
    hs_school_type: Optional[str]


class SchoolList(TypedDict, total=False):
    """``GET /v1/schools`` — the page envelope."""

    data: list[SchoolSummary]
    pagination: dict


class SchoolScores(TypedDict, total=False):
    """One school's yearly assessment snapshot.

    Licensed: the route needs the ``school_licensed`` scope.
    """

    uid: str
    year: int
    rank: Optional[int]
    rank_total: Optional[int]
    rank_score: Optional[float]
    avg_exam_mark: Optional[float]
    year_label: Optional[str]
    source: Optional[str]
    eqao: list[dict]


class SchoolDetail(SchoolSummary, total=False):
    """``GET /v1/schools/{uid}`` — one school, with its contact block.

    ``scores`` is present only with the ``school_licensed`` scope.
    """

    address: Optional[str]
    phone: Optional[str]
    phone2: Optional[str]
    fax: Optional[str]
    website_url: Optional[str]
    boundary_pdf_url: Optional[str]
    principal: Optional[str]
    feeder_schools: Optional[dict]
    extra: Optional[dict]
    scores: list[SchoolScores]


class SchoolBoundary(TypedDict, total=False):
    """``GET /v1/schools/{uid}/boundary`` — the catchment outline.

    Licensed. The geometry is a GeoJSON ``MultiPolygon`` — a school may
    have several catchments, and a bare ``Polygon`` would lose the others.
    """

    uid: str
    name: str
    geometry: Optional[dict]
    polygon_count: int
    point_count: int
    source: Optional[str]
    source_url: Optional[str]
    license: Optional[str]


class CatchmentHit(TypedDict, total=False):
    """One catchment covering a queried point."""

    uid: str
    name: str
    type: Optional[str]
    distance_m: Optional[float]


class CatchmentList(TypedDict, total=False):
    """``GET /v1/schools/at`` — the page envelope."""

    data: list[CatchmentHit]
    pagination: dict


class SchoolTaxonomy(TypedDict, total=False):
    """``GET /v1/schools/taxonomy`` — the vocabulary and the headline counts."""

    boards: list[SchoolBoard]
    types: list[dict]
    program_categories: list[dict]
    stats: dict


class SchoolBoardList(TypedDict, total=False):
    """``GET /v1/schools/boards`` — the page envelope."""

    data: list[SchoolBoard]
    pagination: dict
