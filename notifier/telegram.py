# notifier/telegram.py
from __future__ import annotations
import time
import requests
from typing import Dict

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout: int = 10):
        self.base = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send_signal(self, signal: Dict, retry: int = 2) -> bool:
        """
        signal esperado:
        {
          "symbol": "SOLUSDT",
          "bias": "LONG" | "SHORT",
          "score": 82,
          "timeframe": "1h/4h",
          "entry": 143.25,
          "stop_loss": 137.9,
          "take_profit": 150.5,
          "context": ["EMA20>EMA50", "RSI=56", "ATR%=4.2"],
          "evaluated": 147,
          "eligible": 9,
          "sent": 5
        }
        """
        text = self._format(signal)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
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

    def _format(self, s: Dict) -> str:
        ctx = "\n".join(f"• {c}" for c in s.get("context", []))
        header_emoji = "🟢" if s.get("bias") == "LONG" else "🔴"
        return (
f"{header_emoji} *FUTURES SIGNAL* – {s.get('timeframe','H1/H4')}\n"
f"*{s['symbol']}* ({s['bias']}) — *Score:* {s.get('score','?')}\n\n"
f"*Entry:* `{s['entry']}`\n"
f"*StopLoss:* `{s['stop_loss']}`\n"
f"*TakeProfit:* `{s['take_profit']}`\n\n"
f"*Contexto:*\n{ctx}\n\n"
f"Evaluados: {s.get('evaluated','?')} | Elegibles: {s.get('eligible','?')} | Enviados: {s.get('sent','?')}"
        )
