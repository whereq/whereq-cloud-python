# whereq.cloud — Python SDK

Official Python client for the [WhereQ data cloud](https://whereq.cloud) — the versioned,
metered `/v1` API at **`api.whereq.cloud`**: cost-of-living prices, a cross-region
cost-of-living comparison, trending hot-lists, autos, equities & market data, and more.

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

# Bulk CSV export
csv_text = wq.prices_csv(domain="fuel", region="us")

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

## License

MIT © WhereQ
