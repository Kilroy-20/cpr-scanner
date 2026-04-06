import ccxt
import pandas as pd
import requests
import io
from datetime import datetime

# Initialize Bitget
bitget = ccxt.bitget({'options': {'defaultType': 'swap'}})
ULTRA_NARROW = 0.1
SUPER_NARROW = 0.35
NARROW = 0.75

# Webhooks
DAILY_WEBHOOK = "https://discord.com/api/webhooks/1361051232537542968/L1jebjwpeYtZeLwqbSKpcGPQ-Eq9H3qNHBg_SvigGo7jiHipKGWCGHCB3om0DUjVaFXI"
WEEKLY_WEBHOOK = "https://discord.com/api/webhooks/1361049636466458624/AHMfE0WGUgTC0AvJU2W25AhrUb9KGgimqfm2cU8y2bWG1odOyoHFRFPh37WPy6ARVTw8"
MONTHLY_WEBHOOK = "https://discord.com/api/webhooks/1361065958076321862/4aqHQybkRaGFm4u-3z_uLl8NUkZ6023MIymOtRvV9bCP7NIqs3IBjC9DGmARYW7_oDSL"
COMBO_WEBHOOK = "https://discord.com/api/webhooks/1361188778319941682/amzQDeomNp1flPeT3VvTuFYDim31P8rxPrS5kPf9PR5gNapFb21G9oin4sjHv9AqRj1u"
LOG_WEBHOOK = "https://discord.com/api/webhooks/1361189673984069652/zWCeoLGVIw1-747cGtMoRLyEZ8H4EXpPfd1D3bCzg1E-u8vg1fNstLFl0Fnh8Js9XV3P"

def clean_symbol_for_tv(symbol):
    """Converts 'BTC/USDT:USDT' or 'BTC/USDT' to 'BTCUSDT.P'"""
    base = symbol.split('/')[0]
    return f"{base}USDT.P"

def fetch_symbols():
    return sorted([s['symbol'] for s in bitget.load_markets().values() if '/USDT' in s['symbol'] and s['active']])

def get_width(symbol, tf):
    try:
        data = bitget.fetch_ohlcv(symbol, timeframe=tf, limit=2)
        if not data or len(data) < 2:
            return None
        _, _, high, low, close, _ = data[-2]
        pivot = (high + low + close) / 3
        bc = (high + low) / 2
        tc = 2 * pivot - bc
        width = abs(tc - bc)
        return round((width / close) * 100, 4)
    except:
        return None

def scan(timeframe):
    narrow, super_narrow, ultra_narrow = [], [], []
    symbols = fetch_symbols()
    for sym in symbols:
        w = get_width(sym, timeframe)
        if w is None:
            continue
        if w < ULTRA_NARROW:
            ultra_narrow.append((sym, w))
        elif w < SUPER_NARROW:
            super_narrow.append((sym, w))
        elif w < NARROW:
            narrow.append((sym, w))
    return narrow, super_narrow, ultra_narrow

def format_lines(results, dot):
    """Formats Discord text: 🔵 BTCUSDT.P - 0.05%"""
    return [f"{dot} {clean_symbol_for_tv(s[0])} - {s[1]}%" for s in sorted(results)]

def post_results(title, n, sn, un, webhook, dot, filename):
    msg = f"**{dot} {title} CPR Scan**\n"
    
    # Text for the file upload (Strictly TV format for Watchlist Import)
    file_lines = []
    
    if un:
        msg += f"\n🔴 **Ultra Narrow** ({len(un)}):\n" + "\n".join(format_lines(un, dot))
        file_lines += [clean_symbol_for_tv(s[0]) for s in sorted(un)]
    if sn:
        msg += f"\n🟣 **Super Narrow** ({len(sn)}):\n" + "\n".join(format_lines(sn, dot))
        file_lines += [clean_symbol_for_tv(s[0]) for s in sorted(sn)]
    if n:
        msg += f"\n🔵 **Narrow** ({len(n)}):\n" + "\n".join(format_lines(n, dot))
        file_lines += [clean_symbol_for_tv(s[0]) for s in sorted(n)]

    # Send text message to Discord
    requests.post(webhook, json={"content": msg})
    
    # Create and send .txt file formatted for TradingView Import
    if file_lines:
        file_data = "\n".join(file_lines)
        buf = io.BytesIO(file_data.encode())
        requests.post(webhook, files={"file": (filename, buf, "text/plain")})

def log(message):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{ts}] {message}\n"
    buf = io.BytesIO(log_entry.encode())
    requests.post(LOG_WEBHOOK, files={"file": ("log.txt", buf, "text/plain")})

def combo_report(d, w, m):
    results_text = []
    file_lines = []
    dot_daily, dot_weekly, dot_monthly = "🔵", "🟡", "🔴"
    all_syms = set(x[0] for group in d + w + m for x in group)

    for sym in sorted(all_syms):
        count = sum([
            any(x[0] == sym for x in d[0] + d[1] + d[2]),
            any(x[0] == sym for x in w[0] + w[1] + w[2]),
            any(x[0] == sym for x in m[0] + m[1] + m[2])
        ])
        if count >= 2:
            dots = "".join([
                dot_daily if any(x[0] == sym for x in d[0] + d[1] + d[2]) else "",
                dot_weekly if any(x[0] == sym for x in w[0] + w[1] + w[2]) else "",
                dot_monthly if any(x[0] == sym for x in m[0] + m[1] + m[2]) else ""
            ])
            tv_sym = clean_symbol_for_tv(sym)
            results_text.append(f"{dots} {tv_sym} - Combo Narrow CPR")
            file_lines.append(tv_sym)

    if results_text:
        msg = "**🧩 Combo CPR Matches**\n\n" + "\n".join(results_text)
        requests.post(COMBO_WEBHOOK, json={"content": msg})
        
        # File for Combo results
        file_data = "\n".join(file_lines)
        buf = io.BytesIO(file_data.encode())
        requests.post(COMBO_WEBHOOK, files={"file": ("combo_results.txt", buf, "text/plain")})

def main():
    try:
        dn, ds, du = scan("1d")
        wn, ws, wu = scan("1w")
        mn, ms, mu = scan("1M")

        post_results("Daily", dn, ds, du, DAILY_WEBHOOK, "🔵", "daily_results.txt")
        post_results("Weekly", wn, ws, wu, WEEKLY_WEBHOOK, "🟡", "weekly_results.txt")
        post_results("Monthly", mn, ms, mu, MONTHLY_WEBHOOK, "🔴", "monthly_results.txt")
        combo_report([dn, ds, du], [wn, ws, wu], [mn, ms, mu])
        log("✅ Script ran successfully")
    except Exception as e:
        log(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    main()
