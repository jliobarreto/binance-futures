"""Utilities for downloading macroeconomic indicators."""

from __future__ import annotations

import yfinance as yf


def get_latest_macro_close() -> dict[str, float]:
    """Fetch latest close values for VIX and UUP (proxy for DXY).

    Returns
    -------
    dict[str, float]
        Dictionary with keys ``"vix"`` and ``"uup"`` containing the latest
        closing prices as floats.
    """

    data = yf.download(["^VIX", "UUP"], period="1d", progress=False)

    try:
        vix_close = data["Close"]["^VIX"].iloc[0].item()
        uup_close = data["Close"]["UUP"].iloc[0].item()
    except Exception as exc:  # pragma: no cover - defensive against API changes
        raise ValueError("No se pudieron obtener los cierres de VIX/UUP") from exc

    return {"vix": vix_close, "uup": uup_close}
    