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

## License

MIT © WhereQ
