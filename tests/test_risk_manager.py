from logic.risk_manager import puede_operar
from config import MAX_CONSEC_LOSSES, BTC_DROP_THRESHOLD


def test_permite_operar_bajo_limites():
    assert puede_operar(MAX_CONSEC_LOSSES - 1, BTC_DROP_THRESHOLD / 2)


def test_bloquea_por_perdidas_consecutivas():
    assert puede_operar(MAX_CONSEC_LOSSES, 0) is False


def test_bloquea_por_caida_de_btc():
    assert puede_operar(0, BTC_DROP_THRESHOLD) is False
