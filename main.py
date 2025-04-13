import ccxt
import pandas as pd
import requests
from datetime import datetime

# === CONFIG ===
DAILY_WEBHOOK = "https://discord.com/api/webhooks/1361051232537542968/L1jebjwpeYtZeLwqbSKpcGPQ-Eq9H3qNHBg_SvigGo7jiHipKGWCGHCB3om0DUjVaFXI"
WEEKLY_WEBHOOK = "https://discord.com/api/webhooks/1361049636466458624/AHMfE0WGUgTC0AvJU2W25AhrUb9KGgimqfm2cU8y2bWG1odOyoHFRFPh37WPy6ARVTw8"
MONTHLY_WEBHOOK = "https://discord.com/api/webhooks/1361065958076321862/4aqHQybkRaGFm4u-3z_uLl8NUkZ6023MIymOtRvV9bCP7NIqs3IBjC9DGmARYW7_oDSL"
SUPER_NARROW_THRESHOLD = 0.1
NARROW_THRESHOLD = 0.25

bitget = ccxt.bitget({'options': {'defaultType': 'swap'}})

def fetch_symbols(exchange):
    return [s['symbol'] for s in exchange.load_markets().values() if '/USDT' in s['symbol'] and s['active']]

def fetch_prev_candle(exchange, symbol, tf):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=2)
        if ohlcv:
            _, _, high, low, close, _ = ohlcv[-2]
            pivot = (high + low + close) / 3
            bc = (high + low) / 2
            tc = 2 * pivot - bc
            width = abs(tc - bc)
            width_pct = round((width / close) * 100, 4)
            return width_pct
    except:
        return None

def scan_market(exchange, tf):
    narrow_list, super_narrow_list = [], []
    for symbol in fetch_symbols(exchange):
        width_pct = fetch_prev_candle(exchange, symbol, tf)
        if width_pct is not None:
            if width_pct <= SUPER_NARROW_THRESHOLD:
                super_narrow_list.append(symbol)
            elif width_pct <= NARROW_THRESHOLD:
                narrow_list.append(symbol)
    return narrow_list, super_narrow_list

def send_to_discord(webhook, title, narrow, super_narrow):
    msg = f"**{title} CPR Scan (Bitget)**\n\n"
    msg += f"🟣 **Super Narrow** ({len(super_narrow)}):\n" + "\n".join(super_narrow[:20]) + "\n\n"
    msg += f"🔵 **Narrow** ({len(narrow)}):\n" + "\n".join(narrow[:20])
    requests.post(webhook, json={"content": msg})

def run_daily():
    narrow, super_narrow = scan_market(bitget, "1d")
    send_to_discord(DAILY_WEBHOOK, "Daily", narrow, super_narrow)

def run_weekly():
    narrow, super_narrow = scan_market(bitget, "1w")
    send_to_discord(WEEKLY_WEBHOOK, "Weekly", narrow, super_narrow)

def run_monthly():
    narrow, super_narrow = scan_market(bitget, "1M")
    send_to_discord(MONTHLY_WEBHOOK, "Monthly", narrow, super_narrow)

# === Smart run control ===
today = datetime.utcnow()
weekday = today.weekday()  # Monday = 0
day_of_month = today.day   # 1st = run monthly

if day_of_month == 1:
    run_monthly()

if weekday == 0:
    run_weekly()

run_daily()

