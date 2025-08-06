import pandas as pd
import numpy as np

import logic.market_context as mc


def _make_df(up=True, rows=210):
    values = np.linspace(1, rows, rows)
    if not up:
        values = values[::-1]
    data = {
        "Open": values,
        "High": values + 1,
        "Low": values - 1,
        "Close": values,
        "Volume": np.linspace(100, 100 + rows - 1, rows),
    }
    index = pd.date_range("2020-01-01", periods=rows, freq="D")
    return pd.DataFrame(data, index=index)


def test_obtener_contexto_mercado(monkeypatch):
    btc_d = _make_df(up=True)
    btc_w = _make_df(up=True, rows=60)
    eth_d = _make_df(up=True)
    eth_w = _make_df(up=True, rows=60)
    dxy_d = _make_df(up=False)
    vix_d = _make_df(up=False, rows=120)

    def fake_descargar(ticker: str, interval: str, period: str = "400d"):
        if ticker == "BTC-USD" and interval == "1d":
            return btc_d
        if ticker == "BTC-USD" and interval == "1wk":
            return btc_w
        if ticker == "ETH-USD" and interval == "1d":
            return eth_d
        if ticker == "ETH-USD" and interval == "1wk":
            return eth_w
        if ticker in ("^DXY", "DX-Y.NYB"):
            return dxy_d
        if ticker == "^VIX":
            return vix_d
        return pd.DataFrame()

    monkeypatch.setattr(mc, "_descargar_seguro", fake_descargar)
    monkeypatch.setattr(mc, "registrar_contexto_csv", lambda *a, **k: "")

    ctx = mc.obtener_contexto_mercado()
    assert ctx.apto_long
    assert not ctx.apto_short
    assert ctx.mercado_favorable
