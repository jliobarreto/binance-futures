# check_macro_state.py
from utils.macro import get_macro_state
ms = get_macro_state()
print("VIX last:", ms.vix_last, " | VIX +5d %:", ms.vix_pc5)
print("DXY last:", ms.dxy_last, " | DXY +5d %:", ms.dxy_pc5)
