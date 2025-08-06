from __future__ import annotations

from binance.client import Client


def obtener_top_usdt(client: Client, limit: int | None = None) -> list[str]:
    """Fetch top USDT trading pairs by trading volume.

    Parameters
    ----------
    client: Client
        Binance client instance.
    limit: int | None
        Maximum number of pairs to return. If ``None`` all qualifying
        symbols are returned.
    """
    tickers = client.get_ticker_24hr()  # type: ignore[no-untyped-call]
    usdt_tickers = [t for t in tickers if t.get("symbol", "").endswith("USDT")]
    usdt_tickers.sort(
        key=lambda t: float(t.get("quoteVolume") or t.get("volume") or 0),
        reverse=True,
    )
    symbols = [t["symbol"] for t in usdt_tickers]
    if limit is not None:
        return symbols[:limit]
    return symbols


__all__ = ["obtener_top_usdt"]
