# notifier/telegram.py
from __future__ import annotations
import time
import math
import re
import requests
from typing import Dict, List, Tuple, Optional


class TelegramNotifier:
    """
    Envío de señales a Telegram con metadatos de grids dinámicos.

    Step dinámico:
      step = clamp( ATR% * K , 1.5% , 3.5% )
      - K por defecto = 0.35  (p.ej. ATR%≈6% -> step≈2.1%)
      - Puedes sobreescribir K o los límites vía kwargs del ctor o en el payload.

    Nº de grids:
      n = floor( ln(factor) / ln(1 + step) )
      - factor = TP/Entry (LONG) ; Entry/TP (SHORT)
      - Con límites de seguridad min_grids y max_grids (no fijo a 12).

    Overrides por señal (opcionales):
      - "grid_step": fuerza el step; recalcula n.
      - "grids": fuerza el nº de grids; recalcula step.
      - Si vienen ambos, se respetan ambos (sujeto a clamps de seguridad).
    """

    def __init__(
        self,
        token: str,
        chat_id: str,
        timeout: int = 10,
        *,
        # límites del step dinámico
        min_step_pct: float = 0.015,   # 1.5%
        max_step_pct: float = 0.035,   # 3.5%
        atr_to_step_k: float = 0.35,   # factor para mapear ATR% -> step
        # límites de seguridad para nº de grids
        min_grids: int = 6,
        max_grids: int = 30,
    ):
        self.base = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

        self.min_step_pct = float(min_step_pct)
        self.max_step_pct = float(max_step_pct)
        self.atr_to_step_k = float(atr_to_step_k)
        self.min_grids = int(min_grids)
        self.max_grids = int(max_grids)

    # ==================== API pública ====================

    def send_signal(self, signal: Dict, retry: int = 2) -> bool:
        """
        Payload mínimo:
        {
          "symbol": "SOLUSDT",
          "bias": "LONG" | "SHORT",
          "score": 82.3,
          "entry": 143.25,
          "stop_loss": 137.9,
          "take_profit": 150.5,

          # opcional:
          "atr_pct": 0.061,  # fracción o porcentaje (0.061 o 6.1)
          # overrides:
          "min_step_pct": 0.015, "max_step_pct": 0.035, "atr_to_step_k": 0.35,
          "min_grids": 6, "max_grids": 30,
          "grid_step": 0.02,  # 2% en fracción, si se desea forzar
          "grids": 12,        # si se desea forzar

          # pie del mensaje (independiente por tarjeta):
          "evaluated": 466, "eligible": 18, "sent": 2,

          # contexto adicional:
          "context": ["ADX=31.9", "RR≈2.40R", "ATR%≈0.0434"]
        }
        """
        text = self._format(signal)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        for i in range(retry + 1):
            try:
                r = requests.post(self.base, json=payload, timeout=self.timeout)
                if r.ok:
                    return True
            except Exception:
                pass
            time.sleep(1 + i)
        return False

    # ==================== Formato / lógica ====================

    def _format(self, s: Dict) -> str:
        # Permitir overrides por señal
        min_step = float(s.get("min_step_pct", self.min_step_pct))
        max_step = float(s.get("max_step_pct", self.max_step_pct))
        k_map = float(s.get("atr_to_step_k", self.atr_to_step_k))
        min_n = int(s.get("min_grids", self.min_grids))
        max_n = int(s.get("max_grids", self.max_grids))

        # Cálculo de grids dinámicos (con overrides flexibles)
        n, step, tags = self._grid_meta(
            s,
            min_step=min_step,
            max_step=max_step,
            k_map=k_map,
            min_n=min_n,
            max_n=max_n,
        )

        rr = self._rr_ratio(s)
        rr_txt = f"RR≈{rr:.2f}R" if rr is not None else None

        # Contexto original + prefijo con grids
        ctx_items: List[str] = list(s.get("context", []))
        tag_str = f" ({'|'.join(tags)})" if tags else ""
        grids_line = f"Grids={n}{tag_str} • step≈{step*100:.2f}%"
        ctx_items.insert(0, grids_line)

        atrp = self._extract_atr_pct(s)
        if atrp is not None and not any("ATR%" in str(c) for c in ctx_items):
            ctx_items.append(f"ATR%≈{atrp:.4f}")  # si prefieres porcentaje: f"ATR≈{atrp*100:.2f}%"
        if rr_txt and not any("RR≈" in str(c) for c in ctx_items):
            ctx_items.append(rr_txt)

        # escapar Markdown en el contexto/símbolo para evitar roturas
        ctx = "\n".join(f"• {self._esc(str(c))}" for c in ctx_items)

        header_emoji = "🟢" if str(s.get("bias","")).upper() == "LONG" else "🔴"

        # Título SIN timeframe
        return (
f"{header_emoji} *FUTURES SIGNAL*\n"
f"*{self._esc(str(s['symbol']))}* ({self._esc(str(s['bias']))}) — *Score:* {self._fmt_num(s.get('score','?'))}\n\n"
f"*Entry:* `{self._fmt_num(s['entry'])}`\n"
f"*StopLoss:* `{self._fmt_num(s['stop_loss'])}`\n"
f"*TakeProfit:* `{self._fmt_num(s['take_profit'])}`\n\n"
f"*Contexto:*\n{ctx}\n\n"
f"Evaluados: {s.get('evaluated','?')} | Elegibles: {s.get('eligible','?')} | Enviados: {s.get('sent','?')}"
        )

    # -------------------- helpers --------------------

    def _grid_meta(
        self,
        s: Dict,
        *,
        min_step: float,
        max_step: float,
        k_map: float,
        min_n: int,
        max_n: int,
    ) -> Tuple[int, float, List[str]]:
        """
        Devuelve (n, step, tags)
        - tags ∈ {"cap","min","forced"} (pueden venir varias)
        """
        entry = float(s["entry"])
        tp = float(s["take_profit"])
        bias = str(s.get("bias", "LONG")).upper()

        # factor de distancia multiplicativa hasta TP
        if bias == "LONG":
            factor = max(tp, entry * 1.0005) / max(entry, 1e-12)
        else:
            factor = max(entry, 1e-12) / max(tp, 1e-12)
        factor = max(factor, 1.0005)  # evita log(1)

        tags: List[str] = []

        # Overrides
        o_step = s.get("grid_step")     # esperado como fracción (0.02 = 2%)
        o_n = s.get("grids")            # entero

        # Normalizar override step si viene en porcentaje (>= 0.5 asumo %)
        if isinstance(o_step, (int, float)):
            o_step = float(o_step)
            if o_step > 0.5:  # si pasaron 2 (=200%), es un error; si pasaron 2%, o_step=2 -> 2>0.5 => tratar como 200% -> dividir
                o_step = o_step / 100.0

        # Caso A: vienen ambos -> respetar ambos (con clamp de seguridad)
        if isinstance(o_step, (int, float)) and isinstance(o_n, int) and o_n > 0:
            step = max(min_step, min(max_step, float(o_step)))
            n = max(min_n, min(max_n, int(o_n)))
            if (n != int(o_n)) or (abs(step - float(o_step)) > 1e-12):
                tags.append("forced")
            # marcar min/cap si aplica por clamp del nº
            if n == min_n and int(o_n) < min_n:
                tags.append("min")
            if n == max_n and int(o_n) > max_n:
                tags.append("cap")
            return n, step, tags

        # Caso B: sólo viene grid_step -> fuerza step y recalcula n
        if isinstance(o_step, (int, float)):
            step = max(min_step, min(max_step, float(o_step)))
            if abs(step - float(o_step)) > 1e-12:
                tags.append("forced")
            # nº natural de grids con este step
            n_float = math.log(factor) / math.log(1.0 + step)
            n_nat = max(1, int(math.floor(n_float)))
            n = n_nat
            # aplicar límites
            if n < min_n:
                n = min_n
                tags.append("min")
            elif n > max_n:
                n = max_n
                tags.append("cap")
            return n, step, tags

        # Caso C: sólo viene grids -> fuerza n y calcula step ~ equiespaciado geométrico
        if isinstance(o_n, int) and o_n > 0:
            n = max(min_n, min(max_n, int(o_n)))
            if n != int(o_n):
                tags.append("forced")
            # step ideal para cubrir el factor con n saltos: (1+step)^n = factor
            step_ideal = factor ** (1.0 / max(n, 1)) - 1.0
            step = max(min_step, min(max_step, step_ideal))
            if abs(step - step_ideal) > 1e-12:
                # si el step quedó clamp, marcamos condición (min/cap del step no aparece, dejamos "forced")
                if "forced" not in tags:
                    tags.append("forced")
            return n, step, tags

        # Caso D: sin overrides -> usar ATR% mapeado
        atrp = self._extract_atr_pct(s)            # fracción (0.06 = 6%)
        step = max(min_step, min(max_step, (atrp or 0.0) * k_map))
        step = max(step, min_step)                 # por si no hay ATR en la señal

        # nº "natural" de grids sin fijar a 12
        n_float = math.log(factor) / math.log(1.0 + step)
        n_nat = max(1, int(math.floor(n_float)))

        if n_nat < min_n:
            n = min_n
            tags.append("min")
        elif n_nat > max_n:
            n = max_n
            tags.append("cap")
        else:
            n = n_nat

        return n, step, tags

    def _extract_atr_pct(self, s: Dict) -> Optional[float]:
        """
        Devuelve el ATR% en fracción (0.06 = 6%) desde:
          - s['atr_pct'] numérico
          - o desde líneas de context tipo 'ATR%=0.0618' o 'ATR%≈0.0618' o 'ATR≈6.18%'
        """
        v = s.get("atr_pct")
        if isinstance(v, (int, float)):
            atr = float(v)
            return atr / 100.0 if atr > 0.5 else atr

        # intenta parsear del contexto
        for line in s.get("context", []):
            txt = str(line)
            # ATR%≈0.0618  ó  ATR% = 0.0618
            m = re.search(r"ATR%[≈=]\s*([0-9]*\.?[0-9]+)", txt)
            if m:
                atr = float(m.group(1))
                return atr / 100.0 if atr > 0.5 else atr
            # ATR≈6.18%
            m2 = re.search(r"ATR[≈=]\s*([0-9]*\.?[0-9]+)\s*%", txt)
            if m2:
                atr = float(m2.group(1))
                return atr / 100.0
        return None

    def _rr_ratio(self, s: Dict) -> Optional[float]:
        try:
            e = float(s["entry"]); sl = float(s["stop_loss"]); tp = float(s["take_profit"])
            if str(s.get("bias","")).upper() == "LONG":
                risk = max(e - sl, 1e-12); reward = max(tp - e, 0.0)
            else:
                risk = max(sl - e, 1e-12); reward = max(e - tp, 0.0)
            return reward / risk if risk > 0 else None
        except Exception:
            return None

    def _fmt_num(self, x) -> str:
        try:
            v = float(x)
        except Exception:
            return str(x)
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        if abs(v) >= 100:
            return f"{v:.2f}"
        if abs(v) >= 10:
            return f"{v:.2f}"
        if abs(v) >= 1:
            return f"{v:.4f}"
        return f"{v:.6f}"

    def _esc(self, t: str) -> str:
        """
        Escape básico para 'Markdown' clásico de Telegram en textos dinámicos.
        (No tocar el formato fijo con *...* y `...`.)
        """
        if not isinstance(t, str):
            return str(t)
        return (
            t.replace('\\', r'\\')
             .replace('_', r'\_')
             .replace('*', r'\*')
             .replace('`', r'\`')
             .replace('[', r'\[')
             .replace(']', r'\]')
             .replace('(', r'\(')
             .replace(')', r'\)')
        )
