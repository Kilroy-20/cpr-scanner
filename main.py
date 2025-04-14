import ccxt
import pandas as pd
import requests
from datetime import datetime

bitget = ccxt.bitget({'options': {'defaultType': 'swap'}})
SUPER_NARROW = 0.1
NARROW = 0.25

DAILY_WEBHOOK = "https://discord.com/api/webhooks/1361051232537542968/L1jebjwpeYtZeLwqbSKpcGPQ-Eq9H3qNHBg_SvigGo7jiHipKGWCGHCB3om0DUjVaFXI"
WEEKLY_WEBHOOK = "https://discord.com/api/webhooks/1361049636466458624/AHMfE0WGUgTC0AvJU2W25AhrUb9KGgimqfm2cU8y2bWG1odOyoHFRFPh37WPy6ARVTw8"
MONTHLY_WEBHOOK = "https://discord.com/api/webhooks/1361065958076321862/4aqHQybkRaGFm4u-3z_uLl8NUkZ6023MIymOtRvV9bCP7NIqs3IBjC9DGmARYW7_oDSL"
COMBO_WEBHOOK = "https://discord.com/api/webhooks/1361188778319941682/amzQDeomNp1flPeT3VvTuFYDim31P8rxPrS5kPf9PR5gNapFb21G9oin4sjHv9AqRj1u"
LOG_WEBHOOK = "https://discord.com/api/webhooks/1361189673984069652/zWCeoLGVIw1-747cGtMoRLyEZ8H4EXpPfd1D3bCzg1E-u8vg1fNstLFl0Fnh8Js9XV3P"

def fetch_symbols():
    return [s['symbol'] for s in bitget.load_markets().values() if '/USDT' in s['symbol'] and s['active']]

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
    n, sn = [], []
    for sym in fetch_symbols():
        w = get_width(sym, timeframe)
        if w is None:
            continue
        if w <= SUPER_NARROW:
            sn.append((sym, w))
        elif w <= NARROW:
            n.append((sym, w))
    return n, sn

def format_lines(results, dot):
    return [f"{dot} {s[0]} - {s[1]}%" for s in results]

def post_results(title, narrow, super_narrow, webhook, dot, filename):
    msg = f"**{dot} {title} CPR Scan**\n"
    lines = []
    if super_narrow:
        msg += f"\n🟣 **Super Narrow** ({len(super_narrow)}):\n" + "\n".join(format_lines(super_narrow, dot))
        lines += [f"Super Narrow: {s[0]} - {s[1]}%" for s in super_narrow]
    if narrow:
        msg += f"\n\n🔵 **Narrow** ({len(narrow)}):\n" + "\n".join(format_lines(narrow, dot))
        lines += [f"Narrow: {s[0]} - {s[1]}%" for s in narrow]

    requests.post(webhook, json={"content": msg})
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    with open(filename, "rb") as f:
        requests.post(webhook, files={"file": f})

def log(message):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with open("log.txt", "a") as f:
        f.write(f"[{ts}] {message}\n")
    with open("log.txt", "rb") as f:
        requests.post(LOG_WEBHOOK, files={"file": f})

def combo_report(dn, ds, wn, ws, mn, ms, is_monday, is_first):
    results = []
    dot_daily, dot_weekly, dot_monthly = "🔵", "🟡", "🔴"
    all_syms = set(s[0] for s in dn + ds)

    for sym in all_syms:
        d = any(s[0] == sym for s in dn)
        dsym = any(s[0] == sym for s in ds)
        w = any(s[0] == sym for s in wn)
        wsym = any(s[0] == sym for s in ws)
        m = any(s[0] == sym for s in mn)
        msym = any(s[0] == sym for s in ms)

        if is_first and d and w and m:
            results.append(f"{dot_daily}{dot_weekly}{dot_monthly} {sym} - Narrow CPR Combo")
        elif is_first and dsym and wsym and msym:
            results.append(f"{dot_daily}{dot_weekly}{dot_monthly} {sym} - Super Narrow CPR Combo")
        elif is_monday and d and w:
            results.append(f"{dot_daily}{dot_weekly} {sym} - Narrow CPR Combo")
        elif is_monday and dsym and wsym:
            results.append(f"{dot_daily}{dot_weekly} {sym} - Super Narrow CPR Combo")

    if results:
        with open("combo_results.txt", "w") as f:
            f.write("\n".join(results))
        with open("combo_results.txt", "rb") as f:
            requests.post(COMBO_WEBHOOK, files={"file": f})
        msg = "**🧩 Combo CPR Matches**\n\n" + "\n".join(results)
        requests.post(COMBO_WEBHOOK, json={"content": msg})

def main():
    today = datetime.utcnow()
    is_monday = today.weekday() == 0
    is_first = today.day == 1

    dn, ds = scan("1d")
    wn, ws = scan("1w") if is_monday or is_first else ([], [])
    mn, ms = scan("1M") if is_first else ([], [])

    try:
        post_results("Daily", dn, ds, DAILY_WEBHOOK, "🔵", "daily_results.txt")
        if is_monday:
            post_results("Weekly", wn, ws, WEEKLY_WEBHOOK, "🟡", "weekly_results.txt")
        if is_first:
            post_results("Monthly", mn, ms, MONTHLY_WEBHOOK, "🔴", "monthly_results.txt")
        if is_monday or is_first:
            combo_report(dn, ds, wn, ws, mn, ms, is_monday, is_first)
        log("✅ Script ran successfully")
    except Exception as e:
        log(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    main()
