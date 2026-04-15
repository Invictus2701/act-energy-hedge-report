#!/usr/bin/env python3
"""
scrape_elexys.py
────────────────────────────────────────────────────────────────────
Scrape des prix Settlement quotidiens publiés par Elexys
(https://my.elexys.be/MarketInformation/) pour alimenter le
tableau "Statistics" du Cockpit.

Produits ciblés :
  - Belgian Power Base  : M+1, Q+1, Q+2, Y+1, Y+2, Y+3  (ENDEX)
  - Dutch TTF Nat. Gas  : M+1, Q+1, Q+2, Y+1, Y+2, Y+3  (ICE ENDEX)

Elexys publie deux pages tabulaires publiques (mises à jour ~17h30
chaque jour ouvré) :
  • EndexPower.aspx       (Belgian Power Base futures)
  • EndexContinentalGas.aspx (TTF Natural Gas futures)

Le script :
  1. GET des deux pages avec headers réalistes (anti-403).
  2. Parse le tableau HTML → (produit, settlement, date).
  3. Charge/merge market_history.json (série historique par produit).
  4. Calcule Var D-1, Var W-1 et stats YTD (Avg/Max/Min).
  5. Réécrit market_history.json + statistics-data.json (forme Cockpit).

Sortie : 2 fichiers dans le même dossier que le script.
"""

from __future__ import annotations
import json, re, sys, time, datetime as dt
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────────────────────────
HERE       = Path(__file__).resolve().parent
HISTORY_FP = HERE / "market_history.json"
COCKPIT_FP = HERE / "statistics-data.json"

URLS = {
    "ELECTRICITY": "https://my.elexys.be/MarketInformation/EndexPower.aspx",
    "GAS":         "https://my.elexys.be/MarketInformation/EndexContinentalGas.aspx",
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.elexys.be/",
}

# Libellés des contrats attendus dans les tableaux Elexys
# (les cellules "Product" ressemblent à "Cal-27", "Q2-26", "May-26")
MONTHS = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
          "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}

# ──────────────────────────────────────────────────────────────────
#  Parse helpers
# ──────────────────────────────────────────────────────────────────
def _next_business_day(d: dt.date) -> dt.date:
    d += dt.timedelta(days=1)
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d

def classify(product_label: str, today: dt.date) -> str | None:
    """Transforme 'May-26' / 'Q3-26' / 'Cal-27' en clé M1/Q1/Q2/Y1/Y2/Y3."""
    p = product_label.strip()
    y = today.year % 100

    # Cal-YY = Year
    m = re.match(r"Cal[- ]?(\d{2})$", p, re.I)
    if m:
        diff = int(m.group(1)) - y
        return f"Y{diff}" if 1 <= diff <= 3 else None

    # Qn-YY = Quarter
    m = re.match(r"Q([1-4])[- ]?(\d{2})$", p, re.I)
    if m:
        q, yy = int(m.group(1)), int(m.group(2))
        q_now = (today.month - 1) // 3 + 1
        diff_q = (yy - y) * 4 + (q - q_now)
        return f"Q{diff_q}" if 1 <= diff_q <= 2 else None

    # Mon-YY = Month
    m = re.match(r"([A-Za-z]{3})[- ]?(\d{2})$", p)
    if m and m.group(1).title() in MONTHS:
        mm, yy = MONTHS[m.group(1).title()], int(m.group(2))
        diff_m = (yy - y) * 12 + (mm - today.month)
        return "M1" if diff_m == 1 else None

    return None

def parse_elexys_table(html: str, today: dt.date) -> tuple[dict[str, float], dt.date]:
    """Renvoie {'M1': 83.04, 'Q1': 92.50, ...} + date de settlement."""
    soup = BeautifulSoup(html, "html.parser")

    # Date de règlement affichée dans l'entête (ex: "Settlement 14/04/2026")
    settle_date = today
    hdr = soup.get_text(" ", strip=True)
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", hdr)
    if m:
        settle_date = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    out: dict[str, float] = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2: continue
            label = cells[0]
            key = classify(label, today)
            if not key: continue
            # Le settlement est typiquement la 2e ou 3e cellule numérique
            for raw in cells[1:]:
                raw_norm = raw.replace(",", ".").replace("€", "").strip()
                try:
                    val = float(raw_norm)
                except ValueError:
                    continue
                if 0 < val < 1000:
                    out[key] = val
                    break
    return out, settle_date

# ──────────────────────────────────────────────────────────────────
#  Fetch
# ──────────────────────────────────────────────────────────────────
def fetch_group(group: str) -> tuple[dict[str, float], dt.date]:
    url = URLS[group]
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return parse_elexys_table(r.text, dt.date.today())
        except Exception as e:
            print(f"[WARN] {group} attempt {attempt+1}: {e}", file=sys.stderr)
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"Unable to scrape {group} from {url}")

# ──────────────────────────────────────────────────────────────────
#  History store
# ──────────────────────────────────────────────────────────────────
def load_history() -> dict[str, dict[str, float]]:
    """history[product_code][YYYY-MM-DD] = settlement price"""
    if HISTORY_FP.exists():
        return json.loads(HISTORY_FP.read_text("utf-8"))
    return {}

def save_history(h: dict[str, dict[str, float]]) -> None:
    HISTORY_FP.write_text(json.dumps(h, indent=2, sort_keys=True), "utf-8")

# ──────────────────────────────────────────────────────────────────
#  Statistics
# ──────────────────────────────────────────────────────────────────
def last_business_days(n: int, upto: dt.date) -> list[dt.date]:
    days, d = [], upto
    while len(days) < n:
        if d.weekday() < 5: days.insert(0, d)
        d -= dt.timedelta(days=1)
    return days

def build_cockpit(history: dict[str, dict[str, float]], today: dt.date) -> dict[str, Any]:
    sessions_d = last_business_days(6, today)
    sessions = [{
        "label":   f"{d.day}/{d.month}",
        "weekday": d.strftime("%A"),
        "date":    d.isoformat(),
    } for d in sessions_d]

    def product_block(code: str, label: str):
        series = history.get(code, {})
        prices = [series.get(d.isoformat()) for d in sessions_d]

        # Var D-1 : dernière valeur vs valeur précédente dispo
        var_d1 = var_w1 = None
        sorted_days = sorted(series.keys())
        if len(sorted_days) >= 2:
            last = series[sorted_days[-1]]
            prev = series[sorted_days[-2]]
            if prev: var_d1 = round((last - prev) / prev * 100, 2)
        # Var W-1 : même jour 7j avant
        if sorted_days:
            last_d  = dt.date.fromisoformat(sorted_days[-1])
            target  = last_d - dt.timedelta(days=7)
            ref = series.get(target.isoformat())
            # fallback : plus proche jour ouvré autour de J-7
            if ref is None:
                for delta in (1, -1, 2, -2, 3, -3):
                    ref = series.get((target + dt.timedelta(days=delta)).isoformat())
                    if ref is not None: break
            last = series[sorted_days[-1]]
            if ref: var_w1 = round((last - ref) / ref * 100, 2)

        # YTD : 1er janvier -> today
        ystart = dt.date(today.year, 1, 1).isoformat()
        ytd = [v for k, v in series.items() if k >= ystart and v is not None]
        avg = round(sum(ytd) / len(ytd), 2) if ytd else None
        mx  = round(max(ytd), 2) if ytd else None
        mn  = round(min(ytd), 2) if ytd else None

        return {
            "code": code, "label": label,
            "prices": [round(p, 2) if p is not None else None for p in prices],
            "varD1": var_d1, "varW1": var_w1,
            "avg": avg, "max": mx, "min": mn,
        }

    electricity = [
        product_block("BE_POWER_BASE_M1", "BE M+1 base"),
        product_block("BE_POWER_BASE_Q1", "BE Q+1 base"),
        product_block("BE_POWER_BASE_Q2", "BE Q+2 base"),
        product_block("BE_POWER_BASE_Y1", "BE Y+1 base"),
        product_block("BE_POWER_BASE_Y2", "BE Y+2 base"),
        product_block("BE_POWER_BASE_Y3", "BE Y+3 base"),
    ]
    gas = [
        product_block("TTF_NG_M1", "TTF M+1"),
        product_block("TTF_NG_Q1", "TTF Q+1"),
        product_block("TTF_NG_Q2", "TTF Q+2"),
        product_block("TTF_NG_Y1", "TTF Y+1"),
        product_block("TTF_NG_Y2", "TTF Y+2"),
        product_block("TTF_NG_Y3", "TTF Y+3"),
    ]

    return {
        "meta": {
            "module": "Statistics",
            "generatedAt": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "Elexys - https://my.elexys.be/MarketInformation/",
            "currency": "EUR", "unit": "MWh",
            "ytdStart": f"{today.year}-01-01",
            "sessions": sessions,
        },
        "markets": [
            {"group": "ELECTRICITY", "products": electricity},
            {"group": "GAS",         "products": gas},
        ],
    }

# ──────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────
CODE_MAP = {
    "ELECTRICITY": {"M1":"BE_POWER_BASE_M1","Q1":"BE_POWER_BASE_Q1","Q2":"BE_POWER_BASE_Q2",
                    "Y1":"BE_POWER_BASE_Y1","Y2":"BE_POWER_BASE_Y2","Y3":"BE_POWER_BASE_Y3"},
    "GAS":         {"M1":"TTF_NG_M1","Q1":"TTF_NG_Q1","Q2":"TTF_NG_Q2",
                    "Y1":"TTF_NG_Y1","Y2":"TTF_NG_Y2","Y3":"TTF_NG_Y3"},
}

def main() -> int:
    history = load_history()
    today   = dt.date.today()

    for group in ("ELECTRICITY", "GAS"):
        prices, settle = fetch_group(group)
        print(f"[OK] {group} @ {settle}: {prices}")
        for k, v in prices.items():
            code = CODE_MAP[group].get(k)
            if not code: continue
            history.setdefault(code, {})[settle.isoformat()] = v

    save_history(history)
    cockpit = build_cockpit(history, today)
    COCKPIT_FP.write_text(json.dumps(cockpit, indent=2), "utf-8")
    print(f"[DONE] wrote {HISTORY_FP.name} + {COCKPIT_FP.name}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
