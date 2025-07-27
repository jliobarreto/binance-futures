from __future__ import annotations

import pandas as pd


def valida_entrada_largo_plazo(df_d: pd.DataFrame, df_w: pd.DataFrame) -> tuple[bool, str]:
    """Placeholder validation for long term entry.

    Always returns ``True`` with an empty reason.  In a full
    implementation this function would analyse the dataframes
    to decide whether the asset is suitable for analysis.
    """
    return True, ""
