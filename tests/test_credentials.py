import logging
import sys
import types
from types import SimpleNamespace

# Stub data.symbols before importing contriver
fake_symbols = types.ModuleType("data.symbols")
fake_symbols.obtener_top_usdt = lambda *args, **kwargs: []
sys.modules.setdefault("data.symbols", fake_symbols)

from logic import contriver

def test_run_bot_aborts_without_credentials(monkeypatch, caplog):
    context = SimpleNamespace(
        btc_alcista=True,
        eth_alcista=True,
        dxy_alcista=False,
        vix_valor=10.0,
        score_total=80.0,
        score_long=80.0,
        score_short=20.0,
        apto_long=True,
        apto_short=True,
    )
    monkeypatch.setattr(contriver, "obtener_contexto_mercado", lambda: context)
    monkeypatch.setattr(contriver, "puede_operar", lambda: True)
    called = {}
    def fake_enviar(msg):
        called["msg"] = msg
    monkeypatch.setattr(contriver, "enviar_telegram", fake_enviar)
    def boom(*args, **kwargs):
        raise AssertionError("should not call Binance when credentials missing")
    monkeypatch.setattr(contriver, "obtener_top_usdt", boom)
    with caplog.at_level(logging.ERROR):
        contriver.run_bot()
    assert "Faltan credenciales de Binance" in caplog.text
    assert called["msg"].startswith("⚠️ Se requieren credenciales")
