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
