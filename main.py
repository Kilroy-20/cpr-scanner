import ccxt
import pandas as pd
import requests
from datetime import datetime

bitget = ccxt.bitget({'options': {'defaultType': 'swap'}})
ULTRA_NARROW = 0.1
SUPER_NARROW = 0.35
NARROW = 0.75

DAILY_WEBHOOK = "https://discord.com/api/webhooks/1361051232537542968/L1jebjwpeYtZeLwqbSKpcGPQ-Eq9H3qNHBg_SvigGo7jiHipKGWCGHCB3om0DUjVaFXI"
WEEKLY_WEBHOOK = "https://discord.com/api/webhooks/1361049636466458624/AHMfE0WGUgTC0AvJU2W25AhrUb9KGgimqfm2cU8y2bWG1odOyoHFRFPh37WPy6ARVTw8"
MONTHLY_WEBHOOK = "https://discord.com/api/webhooks/1361065958076321862/4aqHQybkRaGFm4u-3z_uLl8NUkZ6023MIymOtRvV9bCP7NIqs3IBjC9DGmARYW7_oDSL"
COMBO_WEBHOOK = "https://discord.com/api/webhooks/1361188778319941682/amzQDeomNp1flPeT3VvTuFYDim31P8rxPrS5kPf9PR5gNapFb21G9oin4sjHv9AqRj1u"
LOG_WEBHOOK = "https://discord.com/api/webhooks/1361189673984069652/zWCeoLGVIw1-747cGtMoRLyEZ8H4EXpPfd1D3bCzg1E-u8vg1fNstLFl0Fnh8Js9XV3P"

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
    for sym in fetch_symbols():
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
    return [f"{dot} {s[0]} - {s[1]}%" for s in sorted(results)]

def post_results(title, n, sn, un, webhook, dot, filename):
    msg = f"**{dot} {title} CPR Scan**\n"
    lines = []
    if un:
        msg += f"\n🔴 **Ultra Narrow** ({len(un)}):\n" + "\n".join(format_lines(un, dot))
        lines += [f"Ultra Narrow: {s[0]} - {s[1]}%" for s in sorted(un)]
    if sn:
        msg += f"\n🟣 **Super Narrow** ({len(sn)}):\n" + "\n".join(format_lines(sn, dot))
        lines += [f"Super Narrow: {s[0]} - {s[1]}%" for s in sorted(sn)]
    if n:
        msg += f"\n🔵 **Narrow** ({len(n)}):\n" + "\n".join(format_lines(n, dot))
        lines += [f"Narrow: {s[0]} - {s[1]}%" for s in sorted(n)]

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

def combo_report(d, w, m):
    results = []
    dot_daily, dot_weekly, dot_monthly = "🔵", "🟡", "🔴"
    all_syms = set(x[0] for group in d + w + m for x in group)

    for sym in sorted(all_syms):
        count = sum([
            any(x[0] == sym for x in d),
            any(x[0] == sym for x in w),
            any(x[0] == sym for x in m)
        ])
        if count >= 2:
            dots = "".join([
                dot_daily if any(x[0] == sym for x in d) else "",
                dot_weekly if any(x[0] == sym for x in w) else "",
                dot_monthly if any(x[0] == sym for x in m) else ""
            ])
            results.append(f"{dots} {sym} - Combo Narrow CPR")

    if results:
        with open("combo_results.txt", "w") as f:
            f.write("\n".join(results))
        with open("combo_results.txt", "rb") as f:
            requests.post(COMBO_WEBHOOK, files={"file": f})
        msg = "**🧩 Combo CPR Matches**\n\n" + "\n".join(results)
        requests.post(COMBO_WEBHOOK, json={"content": msg})

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
