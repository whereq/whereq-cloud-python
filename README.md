# whereq.cloud — Python SDK

Official Python client for the [WhereQ data cloud](https://whereq.cloud) — the versioned,
metered `/v1` API at **`api.whereq.cloud`**: North-America fuel & gas-station prices,
cost-of-living prices, a cross-region comparison, trending hot-lists, autos, lottery,
equities & market data, and more.

Public endpoints work with no key; metered endpoints take an API key.

## Install

```bash
pip install whereq.cloud
```

## Usage

```python
from whereq_cloud import Client

wq = Client()                          # public access
# wq = Client(api_key="wq_live_…")     # metered tier
# wq = Client()                        # uses $WHEREQ_API_KEY

# Cost of living — compare US states, CA provinces, or metros (by rent-series id)
print(wq.cost_of_living("us:California,ca:Ontario,m:3958"))

# Prices — fuel | food | energy | housing | rent
print(wq.prices(domain="rent", region="us", bedrooms=2, limit=10))
print(wq.price(3958))                  # one series + full history
print(wq.prices(domain="fuel", geo="Calgary, Alberta"))

# Bulk CSV export
csv_text = wq.prices_csv(domain="food", region="us")

# Fuel — North-America gas & diesel: geolocated stations + aggregated series
wq.fuel_stations(country="MX", municipality="Tijuana", product="regular")
wq.fuel_station(1)                     # one station + intra-day price history
wq.fuel_prices(region="mx")            # state / national price series

# Lottery — draws, per-number frequency, and the game registry
wq.lottery_games(country="US", region="NY")
wq.lottery_draws(game="ny_lotto", days=30)
wq.lottery_latest_draw("ny_lotto")
wq.lottery_frequency("ny_lotto", days=365)

# Geography — places, drawable boundaries, and the containment hierarchy
wq.geo_places(kind="ward", country="CA")    # "CA" or "CAN" — either finds Canada
wq.geo_place("osm:r1428125")                # one place + its parents + its children
wq.geo_boundary("osm:r1428125", simplify=50)  # GeoJSON, simplification in METRES
wq.geo_at(lon=-79.38, lat=43.65)            # every place containing a point
wq.geo_concepts()                           # the vocabulary, with live counts
wq.geo_overlaps(bbox="-79.6,43.5,-79.2,43.8")  # pairs covering the same ground

# Discovery
wq.catalog(); wq.categories(); wq.regions(); wq.domains()

# Finance
wq.hotstocks(limit=5)
wq.screener(sector="Technology")

# Escape hatch — call any /v1 endpoint directly
wq.get("/v1/trending", limit=10)
```

Use it as a context manager to close the HTTP connection pool:

```python
with Client(api_key="wq_live_…") as wq:
    data = wq.prices(domain="energy")
```

Errors raise `whereq_cloud.WhereqError` (with `.status`, `.message`, `.url`).

## Fuel stations

Station-level retail fuel prices for **Mexico (`MX`)**, the **United States (`US`)**
and **Canada (`CA`)**. Every price is in **local currency per litre** — `MXN/L`,
`USD/L` or `CAD/L`.

```python
# Canada — by ISO code or by name ("ON" and "Ontario" both match)
wq.fuel_stations(country="CA", state="ON", limit=500)

# United States — every product a station quotes
wq.fuel_stations(country="US", state="TX", product="diesel")

# A map viewport: "minLon,minLat,maxLon,maxLat"
wq.fuel_stations(country="US", bbox="-123,37,-122,38")

# One station's price-change timeline
wq.fuel_station(436335, product="regular", days=7)

# Every matching station, paging for you
for station in wq.iter_fuel_stations(country="CA", product="regular"):
    print(station["name"], station["prices"])
```

Products are `regular`, `midgrade`, `premium` and `diesel` — `FUEL_PRODUCTS`,
`FUEL_COUNTRIES` and `FUEL_CURRENCIES` are exported for convenience.

> **The preview.** Without an entitled API key the fuel endpoints return a
> 100-row preview of the *oldest* rows, ignore `limit`/`offset`, and set
> `demo: true` in the response. Check `response["demo"]` before paging.

`fuel_prices()` is a different thing: the aggregated *series* behind the charts
(EIA weekly for the US, StatCan monthly for Canada, CRE for Mexico), not
station-level prices.

## Geography

Provinces, regions, municipalities, cities, towns, wards and neighbourhoods —
with real, drawable boundaries, and with the places that cover the same ground
kept side by side rather than merged into one.

```python
# The place list. "CA" and "CAN" find the same country, in both vocabularies.
wq.geo_places(kind="city", country="CA", limit=50)
wq.geo_places(source="osm", has_boundary=True)   # only places with an outline

# One place: its containers AND the places inside it
detail = wq.geo_place("osm:r1428125")
print(detail["place"]["name"], len(detail["parents"]), len(detail["children"]))

# The outline as GeoJSON — simplification is in METRES
wq.geo_boundary("osm:r1428125", simplify=50)

# "Which district is this?" — every container, broadest first, none picked
stack = wq.geo_at(lon=-79.38, lat=43.65)
for place in stack["places"]:
    print(place["kind"], place["name"], place.get("country_code"))

# The vocabulary, and the pairs of places covering the same ground
wq.geo_concepts()
wq.geo_overlaps(bbox="-79.6,43.5,-79.2,43.8", min_ratio=0.2)
```

A place belongs to **several** things at once — a neighbourhood is in a ward,
in a city, in a census division, in a province and in a country. `parents` is a
list on purpose. `bbox` is required on `geo_overlaps()`: comparing every pair in
the country is a quadratic join.

## Local

News, events, stories and notices from the configured local feeds, plus the
points of interest from the OpenStreetMap sweep — with their positions.

```python
# The feed — news, events, stories, notices
wq.local_content(type="news", city="Toronto", limit=20)
wq.local_content(q="storm", has_location=True)

# One item, with its tags
wq.local_content_item(42)

# The points of interest. lat/lng/radius_km go together.
wq.local_places(category="food", limit=50)
wq.local_places(lat=43.65, lng=-79.38, radius_km=5)

# One place, the configured feeds, and the vocabulary
wq.local_place(7)
wq.local_sources()
wq.local_taxonomy()
```

## Schools

The school boards' own published directories: the name, the board, the type,
the grade range, the programmes, the contact block and the position.

```python
# The directory
wq.schools(board="ycdsb", type="secondary", limit=50)
wq.schools(q="theresa", has_boundary=True)

# The board registry, and the vocabulary
wq.school_boards()
wq.school_taxonomy()

# One school. The uid is board-qualified and carries a slash.
wq.school("ycdsb/0158")

# The catchments and the scores — these need the `school_licensed` scope.
wq.schools_at(lat=43.89, lng=-79.47)
wq.school_boundary("ycdsb/0158", simplify=50)
wq.school_scores("ycdsb/0158", year=2024)
```

### The two licence tiers

The school data splits in two, and the split is by licence:

- **The open tier** — the name, the board, the type, the grade range, the
  programmes, the address, the contact block, the position. The boards
  publish these on their own websites. Scope: `school`.
- **The licensed tier** — the catchment polygons and the assessment
  scores. The catchment maps are the boards' licensed data (**viewing, not
  redistribution**), and the scores come from a commercially-encumbered
  feed. Scope: `school_licensed`, which is **internal-only** — it is never
  granted to a customer-facing key.

So the behaviour is:

- A key **without** `school_licensed` gets the school back with the `hs_*`
  fields **absent** — not null, absent — and `school_boundary()`,
  `school_scores()` and `schools_at()` raise a `WhereqError` with status
  **403**.
- A key **with** `school_licensed` gets the scores and the polygons.

A valid key that lacks the scope gets 403, not 401: 401 means "who are
you", and a client that gets 401 retries with different credentials.


## License

MIT © WhereQ
