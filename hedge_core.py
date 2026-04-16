#!/usr/bin/env python3
"""
hedge_core.py
────────────────────────────────────────────────────────────────────
Logique partagée entre :
  • load_history_xls.py   — seed initial depuis les .xls
  • scrape_elexys.py      — mise à jour quotidienne Elexys

Clé de voûte : TOUS les prix sont stockés dans market_history.json avec
des codes ABSOLUS (contrats réels), jamais rolling. Ex. :
    BE_POWER|MONTH|2026|05
    BE_POWER|QTR|2026|3
    BE_POWER|CAL|2027
    TTF|MONTH|2026|05
    TTF|CAL|2027

Les codes rolling (M+1/Q+1/Y+1…) sont résolus dynamiquement au
moment d'afficher le cockpit, selon la date d'observation. Ce choix
évite toute discontinuité dans les séries temporelles.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

HERE       = Path(__file__).resolve().parent
HISTORY_FP = HERE / "market_history.json"
COCKPIT_FP = HERE / "statistics-data.json"
COCKPIT_JS = HERE / "statistics-data.js"

PREFIX_ELEC = "BE_POWER"
PREFIX_GAS  = "TTF"

MONTHS_NAME = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


# ──────────────────────────────────────────────────────────────────
#  Historique : load / save / upsert
# ──────────────────────────────────────────────────────────────────
def load_history() -> dict[str, dict[str, float]]:
    if HISTORY_FP.exists():
        return json.loads(HISTORY_FP.read_text("utf-8"))
    return {}


def save_history(history: dict[str, dict[str, float]]) -> None:
    HISTORY_FP.write_text(
        json.dumps(history, indent=2, sort_keys=True), "utf-8"
    )


def upsert(history: dict, code: str, date_iso: str, value: float) -> bool:
    """Insère ou met à jour un point. Retourne True si changement."""
    series = history.setdefault(code, {})
    old = series.get(date_iso)
    if old == round(float(value), 3):
        return False
    series[date_iso] = round(float(value), 3)
    return True


# ──────────────────────────────────────────────────────────────────
#  Mapping rolling (M+1/Q+1/Y+1…) pour une date d'observation
# ──────────────────────────────────────────────────────────────────
def rolling_code(prefix: str, rel: str, asof: dt.date) -> str | None:
    """
    Résout un code relatif en code absolu selon la date d'observation.

    Ex. rolling_code('BE_POWER','M1', 2026-04-15) -> 'BE_POWER|MONTH|2026|05'
        rolling_code('TTF','Y1', 2026-04-15)      -> 'TTF|CAL|2027'
    """
    if rel.startswith("M"):
        n = int(rel[1:])
        mm = asof.month + n
        yy = asof.year + (mm - 1) // 12
        mm = ((mm - 1) % 12) + 1
        return f"{prefix}|MONTH|{yy}|{mm:02d}"
    if rel.startswith("Q"):
        n = int(rel[1:])
        q_now = (asof.month - 1) // 3 + 1
        q = q_now + n
        yy = asof.year + (q - 1) // 4
        q = ((q - 1) % 4) + 1
        return f"{prefix}|QTR|{yy}|{q}"
    if rel.startswith("Y"):
        n = int(rel[1:])
        return f"{prefix}|CAL|{asof.year + n}"
    return None


# ──────────────────────────────────────────────────────────────────
#  Cockpit
# ──────────────────────────────────────────────────────────────────
def last_business_days(n: int, upto: dt.date) -> list[dt.date]:
    days, d = [], upto
    while len(days) < n:
        if d.weekday() < 5:
            days.insert(0, d)
        d -= dt.timedelta(days=1)
    return days


def _product_block(history, prefix, rel, label, asof, sessions_d):
    code = rolling_code(prefix, rel, asof)
    series = history.get(code, {})
    prices = [series.get(d.isoformat()) for d in sessions_d]

    sorted_days = sorted(series.keys())
    var_d1 = var_w1 = None
    if len(sorted_days) >= 2:
        last = series[sorted_days[-1]]
        prev = series[sorted_days[-2]]
        if prev:
            var_d1 = round((last - prev) / prev * 100, 2)
    if sorted_days:
        last_d = dt.date.fromisoformat(sorted_days[-1])
        target = last_d - dt.timedelta(days=7)
        ref = series.get(target.isoformat())
        if ref is None:
            for delta in (1, -1, 2, -2, 3, -3):
                ref = series.get((target + dt.timedelta(days=delta)).isoformat())
                if ref is not None:
                    break
        last = series[sorted_days[-1]]
        if ref:
            var_w1 = round((last - ref) / ref * 100, 2)

    ystart = dt.date(asof.year, 1, 1).isoformat()
    ytd = [v for k, v in series.items() if k >= ystart and v is not None]
    avg = round(sum(ytd) / len(ytd), 2) if ytd else None
    mx  = round(max(ytd), 2) if ytd else None
    mn  = round(min(ytd), 2) if ytd else None

    return {
        "code":    f"{prefix}_{rel}",
        "label":   label,
        "absCode": code,
        "prices":  [round(p, 2) if p is not None else None for p in prices],
        "varD1":   var_d1,
        "varW1":   var_w1,
        "avg":     avg,
        "max":     mx,
        "min":     mn,
    }


def build_cockpit(history: dict[str, dict[str, float]],
                  asof: dt.date,
                  source_label: str) -> dict[str, Any]:
    sessions_d = last_business_days(6, asof)
    sessions = [{
        "label":   f"{d.day}/{d.month}",
        "weekday": d.strftime("%A"),
        "date":    d.isoformat(),
    } for d in sessions_d]

    electricity = [
        _product_block(history, PREFIX_ELEC, "M1", "BE M+1 base", asof, sessions_d),
        _product_block(history, PREFIX_ELEC, "Q1", "BE Q+1 base", asof, sessions_d),
        _product_block(history, PREFIX_ELEC, "Q2", "BE Q+2 base", asof, sessions_d),
        _product_block(history, PREFIX_ELEC, "Y1", "BE Y+1 base", asof, sessions_d),
        _product_block(history, PREFIX_ELEC, "Y2", "BE Y+2 base", asof, sessions_d),
        _product_block(history, PREFIX_ELEC, "Y3", "BE Y+3 base", asof, sessions_d),
    ]
    gas = [
        _product_block(history, PREFIX_GAS, "M1", "TTF M+1", asof, sessions_d),
        _product_block(history, PREFIX_GAS, "Q1", "TTF Q+1", asof, sessions_d),
        _product_block(history, PREFIX_GAS, "Q2", "TTF Q+2", asof, sessions_d),
        _product_block(history, PREFIX_GAS, "Y1", "TTF Y+1", asof, sessions_d),
        _product_block(history, PREFIX_GAS, "Y2", "TTF Y+2", asof, sessions_d),
        _product_block(history, PREFIX_GAS, "Y3", "TTF Y+3", asof, sessions_d),
    ]

    return {
        "meta": {
            "module":      "Statistics",
            "generatedAt": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source":      source_label,
            "asof":        asof.isoformat(),
            "currency":    "EUR",
            "unit":        "MWh",
            "ytdStart":    f"{asof.year}-01-01",
            "sessions":    sessions,
        },
        "markets": [
            {"group": "ELECTRICITY", "products": electricity},
            {"group": "GAS",         "products": gas},
        ],
    }


def latest_settle_date(history: dict[str, dict[str, float]]) -> dt.date | None:
    """Renvoie la date de settlement la plus récente dans l'historique."""
    latest = None
    for series in history.values():
        for d_str in series:
            d = dt.date.fromisoformat(d_str)
            if latest is None or d > latest:
                latest = d
    return latest


def write_cockpit(history: dict, asof: dt.date, source_label: str) -> None:
    # Utilise la dernière date avec données plutôt que "aujourd'hui"
    # pour que le tableau affiche 6 colonnes remplies.
    last = latest_settle_date(history)
    effective_asof = min(asof, last) if last else asof
    payload = json.dumps(build_cockpit(history, effective_asof, source_label), indent=2)
    COCKPIT_FP.write_text(payload, "utf-8")
    # Fichier .js chargeable via <script> — fonctionne aussi en file://
    COCKPIT_JS.write_text(
        f"// Auto-generated by hedge_core — do not edit\n"
        f"window.__STATISTICS_DATA__ = {payload};\n",
        "utf-8",
    )
