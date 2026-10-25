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


class FuelStation(TypedDict):
    """A geolocated retail fuel station and its latest prices.

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
    prices: dict[str, FuelStationPrice]


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
    station: FuelStation
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
