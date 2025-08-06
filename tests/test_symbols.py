import sys

sys.modules.pop("data.symbols", None)
from data.symbols import obtener_top_usdt


class FakeClient:
    def __init__(self, tickers):
        self._tickers = tickers

    def get_ticker_24hr(self):
        return self._tickers


def test_obtener_top_usdt_orders_by_volume_descending():
    tickers = [
        {"symbol": "AAAUSDT", "quoteVolume": "100"},
        {"symbol": "BBBUSDT", "volume": "300"},
        {"symbol": "CCCUSDT", "quoteVolume": "200"},
        {"symbol": "DDDUSDT", "quoteVolume": "400"},
        {"symbol": "EEEUSDT", "volume": "50"},
    ]
    client = FakeClient(tickers)
    result = obtener_top_usdt(client, limit=3)
    assert result == ["DDDUSDT", "BBBUSDT", "CCCUSDT"]


def test_obtener_top_usdt_respects_limit():
    tickers = [
        {"symbol": "AAAUSDT", "quoteVolume": "100"},
        {"symbol": "BBBUSDT", "volume": "300"},
        {"symbol": "CCCUSDT", "quoteVolume": "200"},
    ]
    client = FakeClient(tickers)
    result = obtener_top_usdt(client, limit=2)
    assert result == ["BBBUSDT", "CCCUSDT"]
    assert len(result) == 2
