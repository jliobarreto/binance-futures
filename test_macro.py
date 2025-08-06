import pandas as pd
import yfinance as yf

from utils.macro import get_latest_macro_close


def test_get_latest_macro_close(monkeypatch):
    sample = pd.DataFrame({
        ("Close", "^VIX"): [17.0],
        ("Close", "UUP"): [30.0],
    })

    def fake_download(tickers, period="1d", progress=False):
        return sample

    monkeypatch.setattr(yf, "download", fake_download)

    data = get_latest_macro_close()
    assert data == {"vix": 17.0, "uup": 30.0}
