"""Offline tests — exercise the client against a mock transport (no network)."""
import httpx

from whereq_cloud import Client, WhereqError, __version__


def _client(handler) -> Client:
    c = Client(api_key="wq_test_key")
    c._http = httpx.Client(transport=httpx.MockTransport(handler),
                           base_url="https://api.whereq.cloud",
                           headers=c._http.headers)
    return c


def test_version():
    assert __version__


def test_get_drops_none_params_and_sends_key():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json={"ok": True})

    out = _client(handler).prices(domain="rent", region=None, bedrooms=2)
    assert out == {"ok": True}
    assert "domain=rent" in captured["url"] and "bedrooms=2" in captured["url"]
    assert "region" not in captured["url"]          # None dropped
    assert captured["key"] == "wq_test_key"


def test_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"detail": "quota reached"})

    try:
        _client(handler).prices(domain="rent")
        assert False, "expected WhereqError"
    except WhereqError as e:
        assert e.status == 402 and "quota reached" in e.message


def test_cost_of_living_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/cost-of-living"
        assert "places=us%3ACalifornia" in str(request.url)
        return httpx.Response(200, json={"places": []})

    _client(handler).cost_of_living("us:California")


def test_prices_passes_geo():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    _client(handler).prices(domain="fuel", geo="Calgary, Alberta")
    assert "domain=fuel" in captured["url"]
    assert "geo=Calgary%2C+Alberta" in captured["url"]


def test_fuel_stations_sends_every_filter():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"as_of": "now", "count": 0, "stations": []})

    _client(handler).fuel_stations(
        country="CA", state="ON", municipality="Mississauga",
        product="midgrade", bbox="-80,43,-79,44", q="husky", limit=250, offset=500)

    assert captured["path"] == "/v1/fuel/stations"
    url = captured["url"]
    for fragment in ("country=CA", "state=ON", "municipality=Mississauga",
                     "product=midgrade", "bbox=-80%2C43%2C-79%2C44",
                     "q=husky", "limit=250", "offset=500"):
        assert fragment in url, f"{fragment} missing from {url}"


def test_fuel_station_passes_product_and_days():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"station": {}, "prices": []})

    _client(handler).fuel_station(436335, product="regular", days=7)
    assert captured["path"] == "/v1/fuel/stations/436335"
    assert "product=regular" in captured["url"]
    assert "days=7" in captured["url"]


def test_fuel_prices_forces_the_fuel_domain():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    _client(handler).fuel_prices(region="ca", limit=10)
    assert "domain=fuel" in captured["url"]
    assert "region=ca" in captured["url"]
    assert "limit=10" in captured["url"]


def test_iter_fuel_stations_pages_until_total():
    pages = [
        {"as_of": "t0", "count": 2, "total": 3,
         "stations": [{"id": 1}, {"id": 2}]},
        {"as_of": "t1", "count": 1, "total": 3,
         "stations": [{"id": 3}]},
    ]
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=pages[len(seen) - 1])

    out = list(_client(handler).iter_fuel_stations(page_size=2, country="CA"))
    assert [s["id"] for s in out] == [1, 2, 3]
    assert len(seen) == 2                     # stops once total is reached
    assert "offset=0" in seen[0] and "offset=2" in seen[1]
    assert "country=CA" in seen[0]


def test_iter_fuel_stations_stops_on_an_empty_page():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={"as_of": "t", "count": 0, "total": None,
                                         "stations": []})

    assert list(_client(handler).iter_fuel_stations()) == []
    assert len(calls) == 1


def test_iter_fuel_stations_stops_on_the_demo_preview():
    """The preview returns the same 100 rows for every offset — stop, don't loop."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json={
            "demo": True, "preview_rows": 100, "total": None, "count": 2,
            "as_of": "t", "stations": [{"id": 1}, {"id": 2}]})

    out = list(_client(handler).iter_fuel_stations(country="CA"))
    assert [s["id"] for s in out] == [1, 2]
    assert len(calls) == 1


def test_lottery_paths():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, str(request.url)))
        return httpx.Response(200, json={"count": 0})

    c = _client(handler)
    c.lottery_draws(game="powerball", days=7, limit=5)
    c.lottery_latest_draw("powerball")
    c.lottery_frequency("powerball", days=90)
    c.lottery_games(country="US", region="NY")
    c.lottery_game("powerball")

    assert seen[0][0] == "/v1/lottery/draws"
    assert "game=powerball" in seen[0][1] and "days=7" in seen[0][1]
    assert seen[1][0] == "/v1/lottery/draws/powerball/latest"
    assert seen[2][0] == "/v1/lottery/draws/powerball/frequency"
    assert "days=90" in seen[2][1]
    assert seen[3][0] == "/v1/lottery/games"
    assert "country=US" in seen[3][1] and "region=NY" in seen[3][1]
    assert seen[4][0] == "/v1/lottery/games/powerball"


def test_version_matches_pyproject():
    """The published version and the module's __version__ must not drift."""
    import pathlib
    import re

    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    match = re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.M)
    assert match, "no version found in pyproject.toml"
    assert __version__ == match.group(1)


def test_api_key_falls_back_to_the_environment(monkeypatch):
    monkeypatch.setenv("WHEREQ_API_KEY", "wq_env_key")
    c = Client()
    assert c._http.headers["x-api-key"] == "wq_env_key"
    # An explicit key still wins over the environment.
    c2 = Client(api_key="wq_explicit")
    assert c2._http.headers["x-api-key"] == "wq_explicit"
    c.close()
    c2.close()


# -- geography ------------------------------------------------------------------

def test_geo_places_sends_every_filter():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"count": 0, "data": [], "limit": 50, "offset": 0})

    _client(handler).geo_places(
        kind="ward", source="osm", country="CA", q="yonge",
        bbox="-79.6,43.5,-79.2,43.8", has_boundary=True, limit=200, offset=20)

    assert captured["path"] == "/v1/geo/places"
    url = captured["url"]
    for fragment in ("kind=ward", "source=osm", "country=CA", "q=yonge",
                     "bbox=-79.6%2C43.5%2C-79.2%2C43.8",
                     "has_boundary=true", "limit=200", "offset=20"):
        assert fragment in url, f"{fragment} missing from {url}"


def test_geo_places_drops_the_filters_it_was_not_given():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"count": 0, "data": [], "limit": 50, "offset": 0})

    _client(handler).geo_places(kind="city")
    assert "kind=city" in captured["url"]
    assert "country" not in captured["url"]
    assert "bbox" not in captured["url"]


def test_geo_place_returns_the_place_with_its_parents_and_children():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={
            "uid": "osm:r1428125",
            "place": {"uid": "osm:r1428125", "kind": "country", "name": "Canada"},
            "parents": [],
            "children": [{"uid": "osm:r1", "kind": "city", "name": "Ajax",
                          "source": "osm", "area_ratio": 1.0, "is_primary": False}],
        })

    out = _client(handler).geo_place("osm:r1428125")
    assert captured["path"] == "/v1/geo/places/osm:r1428125"
    assert out["place"]["name"] == "Canada"
    # The parents are a LIST: a place belongs to several things at once.
    assert isinstance(out["parents"], list)
    assert out["children"][0]["name"] == "Ajax"


def test_geo_boundary_passes_simplify_in_metres():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    out = _client(handler).geo_boundary("osm:r1428125", simplify=50)
    assert captured["path"] == "/v1/geo/places/osm:r1428125/boundary"
    assert "simplify=50" in captured["url"]
    assert out["type"] == "FeatureCollection"


def test_geo_at_sends_the_point():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"lon": -79.38, "lat": 43.65, "count": 0, "places": []})

    _client(handler).geo_at(-79.38, 43.65)
    assert captured["path"] == "/v1/geo/at"
    assert "lon=-79.38" in captured["url"]
    assert "lat=43.65" in captured["url"]


def test_geo_concepts():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/geo/concepts"
        return httpx.Response(200, json={"count": 1, "concepts": [], "sources": []})

    out = _client(handler).geo_concepts()
    assert out["count"] == 1


def test_geo_overlaps_sends_the_box():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"bbox": {}, "min_ratio": 0.05,
                                         "count": 0, "overlaps": []})

    _client(handler).geo_overlaps("-79.6,43.5,-79.2,43.8", min_ratio=0.2, limit=50)
    assert captured["path"] == "/v1/geo/overlaps"
    url = captured["url"]
    assert "bbox=-79.6%2C43.5%2C-79.2%2C43.8" in url
    assert "min_ratio=0.2" in url
    assert "limit=50" in url
