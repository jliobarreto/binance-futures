+23
-2

from __future__ import annotations

from config import BTC_DROP_THRESHOLD, MAX_CONSEC_LOSSES


def puede_operar(consecutive_losses: int = 0, btc_drawdown: float = 0.0) -> bool:
    """Determina si se permite operar según límites de riesgo.

    Parameters
    ----------
    consecutive_losses:
        Número de pérdidas consecutivas registradas.
    btc_drawdown:
        Caída porcentual de BTC respecto a su máximo reciente (0.05 = 5%).

    Returns
    -------
    bool
        ``True`` si no se superan los límites configurados, ``False`` en caso
        contrario.
    """

    if consecutive_losses >= MAX_CONSEC_LOSSES:
        return False
    if btc_drawdown >= BTC_DROP_THRESHOLD:
        return False
    return True
