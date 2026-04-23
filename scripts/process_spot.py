#!/usr/bin/env python3
"""
process_spot.py
────────────────────────────────────────────────────────────────────
Normalise les 4 rapports Spot Luminus et produit data/spot-data.json
consomme par l'onglet "Spot" du Cockpit.

Entrees (derniers data/raw/YYYY-MM-DD/) :
  - BelpexHourlyCurrent.xls  : 168 heures x N semaines (header = "Week NN")
  - BelpexM_avg.xls          : long format (Month, quote, Year)
  - GasTtfDah.xls            : time series journaliere (Date, Price)
  - GasTtfDahM_avg.xls       : long format (Month, quote, Year)

Sortie : data/spot-data.json
  {
    "meta": {...},
    "belpexHourly":   {"xLabels": [...], "weeks": [{label, values}, ...]},
    "ttfDahDaily":    {"xLabels": [...], "weeks": [{label, values}, ...]},
    "belpexMonthly":  {"years": [{year, values[12]}, ...]},
    "ttfDahMonthly":  {"years": [{year, values[12]}, ...]}
  }

Usage :
  python scripts/process_spot.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT      = Path(__file__).resolve().parents[1]
RAW_DIR   = ROOT / "data" / "raw"
OUT_FP    = ROOT / "data" / "spot-data.json"

MONTHS_EN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
WEEKDAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


# ──────────────────────────────────────────────────────────────────
#  IO helpers
# ──────────────────────────────────────────────────────────────────
def _read_xls(path: Path) -> pd.DataFrame:
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    sheets = pd.read_excel(path, sheet_name=None, header=None, engine=engine)
    return next(iter(sheets.values()))


def _latest_raw_dir() -> Path:
    days = sorted(d for d in RAW_DIR.iterdir() if d.is_dir() and d.name[0].isdigit())
    if not days:
        raise SystemExit("[FATAL] aucun dossier data/raw/YYYY-MM-DD/ trouve.")
    return days[-1]


def _to_float(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _avg(values, predicate=None):
    """Moyenne des valeurs non-nulles, eventuellement filtrees par predicate(idx)."""
    filtered = [
        v for i, v in enumerate(values)
        if v is not None and (predicate is None or predicate(i))
    ]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 2)


# ──────────────────────────────────────────────────────────────────
#  Parsers
# ──────────────────────────────────────────────────────────────────
def _iso_week_range(year: int, week: int) -> tuple[dt.date, dt.date]:
    """Renvoie (lundi, dimanche) d'une semaine ISO donnee."""
    monday = dt.date.fromisocalendar(year, week, 1)
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


def parse_belpex_hourly(df: pd.DataFrame) -> dict:
    """Belpex 168h par semaine.
    Header : ['Start Date', 'Week 16', 'Week 17'].
    Body   : ['Mon 00:00', 115, 131.92], ..., ['Sun 23:00', ...]."""
    import re

    header = df.iloc[0].tolist()
    body   = df.iloc[1:].reset_index(drop=True)

    # Translate "Mon 00:00" -> "Lun 00:00"
    x_labels: list[str] = []
    for raw in body.iloc[:, 0].tolist():
        s = str(raw).strip()
        for en, fr in zip(WEEKDAYS_EN, WEEKDAYS_FR):
            if s.startswith(en):
                s = s.replace(en, fr, 1)
                break
        x_labels.append(s)

    # Annee de reference : la plus recente possible compatible avec les numeros
    # de semaine presents. Luminus publie la semaine courante + la precedente,
    # donc les N de semaine correspondent a l'annee courante sauf en tout
    # debut d'annee (cas bord : semaine 1 apres semaine 52 -> annee N+1).
    today = dt.date.today()
    today_year, today_week, _ = today.isocalendar()

    weeks = []
    for j in range(1, len(header)):
        raw_label = str(header[j]).strip()
        fr_label  = raw_label.replace("Week", "Semaine")

        m = re.search(r"(\d{1,2})", raw_label)
        if m:
            wk = int(m.group(1))
            # Choix de l'annee : si wk > today_week + 2, c'est de l'annee
            # precedente (cas du passage decembre -> janvier).
            year = today_year
            if wk > today_week + 2:
                year -= 1
            try:
                mon, sun = _iso_week_range(year, wk)
                fr_label = (
                    f"Semaine {wk} "
                    f"({mon.day:02d}/{mon.month:02d} -> "
                    f"{sun.day:02d}/{sun.month:02d})"
                )
            except ValueError:
                pass

        values = [_to_float(v) for v in body.iloc[:, j].tolist()]
        weeks.append({"label": fr_label, "values": values})

    return {"xLabels": x_labels, "weeks": weeks}


def parse_monthly_avg(df: pd.DataFrame, keep_last_n_years: int = 3) -> dict:
    """Long format : [Month, quote, Year] -> {years: [{year, values[12]}]}.
    Retourne les 3 dernieres annees civiles."""
    body = df.iloc[1:].dropna(subset=[0, 2])

    by_year: dict[int, list[float | None]] = {}
    for _, row in body.iterrows():
        month = str(row[0]).strip()[:3]
        try:
            year = int(row[2])
        except (ValueError, TypeError):
            continue
        if month not in MONTHS_EN:
            continue
        by_year.setdefault(year, [None] * 12)
        by_year[year][MONTHS_EN.index(month)] = _to_float(row[1])

    selected_years = sorted(by_year.keys())[-keep_last_n_years:]
    years = [{"year": y, "values": by_year[y]} for y in selected_years]
    return {"years": years}


def build_weekly_slope(belpex_hourly: dict, ttf_daily: dict) -> dict:
    """Reduit les 2 semaines Belpex (168h) + TTF DAH (7j) en moyennes hebdo :
       - Gaz Base         : moyenne des 7 prix journaliers
       - Electricite Base : moyenne des 168 prix horaires
       - Electricite Peak : moyenne des heures 8..19 (12 heures/jour x 7 = 84)
       - Electricite Off-peak : moyenne des heures 20..7 (84 heures)
    Produit une structure prete pour un Slope Chart (2 colonnes + N series)."""
    if not belpex_hourly or not belpex_hourly.get("weeks"):
        return None

    weeks_info = []
    # Convention tarifaire belge (HP / HC) appliquee 7j/7, week-ends inclus :
    #   HP (Heures Pleines) : 07h-11h ET 17h-22h  -> 9h/jour => 63h/semaine
    #   HC (Heures Creuses) : 22h-07h ET 11h-17h  -> 15h/jour => 105h/semaine
    # L'indice horaire i va de 0 (Lun 00h) a 167 (Dim 23h).
    def hour_of(i): return i % 24
    def is_hp(h):   return (7 <= h <= 10) or (17 <= h <= 21)
    peak_pred    = lambda i: is_hp(hour_of(i))
    offpeak_pred = lambda i: not is_hp(hour_of(i))

    elec_base = []
    elec_peak = []
    elec_off  = []
    week_labels = []
    for w in belpex_hourly["weeks"]:
        vals = w["values"]
        elec_base.append(_avg(vals))
        elec_peak.append(_avg(vals, peak_pred))
        elec_off.append(_avg(vals, offpeak_pred))
        week_labels.append(w["label"])
        weeks_info.append({"label": w["label"]})

    # Moyenne hebdo Gaz Base alignee sur les memes labels de semaine.
    # On suppose que ttf_daily.weeks contient les 2 memes semaines ISO.
    gas_base = [None, None]
    if ttf_daily and ttf_daily.get("weeks"):
        for i, w in enumerate(ttf_daily["weeks"][: len(week_labels)]):
            gas_base[i] = _avg(w["values"])

    series = [
        {"code": "GAS_BASE",     "label": "Gaz (Base)",          "group": "GAS",  "values": gas_base},
        {"code": "ELEC_BASE",    "label": "Électricité (Base)",  "group": "ELEC", "values": elec_base},
        {"code": "ELEC_PEAK",    "label": "Électricité (HP)",    "group": "ELEC", "values": elec_peak},
        {"code": "ELEC_OFFPEAK", "label": "Électricité (HC)",    "group": "ELEC", "values": elec_off},
    ]

    # Delta et delta % calcules ici pour que le frontend n'ait qu'a afficher.
    for s in series:
        v0, v1 = s["values"][0], s["values"][-1]
        if v0 is not None and v1 is not None and v0 != 0:
            s["delta"]    = round(v1 - v0, 2)
            s["deltaPct"] = round((v1 - v0) / v0 * 100, 2)
        else:
            s["delta"]    = None
            s["deltaPct"] = None

    return {"weeks": weeks_info, "series": series}


def parse_ttf_daily(df: pd.DataFrame) -> dict:
    """Time series TTF DAH journaliere. On renvoie les 2 dernieres semaines
    ISO completes pour une comparaison jour par jour (Lun->Dim)."""
    body = df.iloc[1:].dropna(subset=[0, 1]).copy()
    body[0] = pd.to_datetime(body[0], dayfirst=True, errors="coerce")
    body = body.dropna(subset=[0]).sort_values(0)

    # Mapping date -> prix
    by_date = {d.date(): _to_float(p) for d, p in zip(body[0], body[1])}
    if not by_date:
        return {"xLabels": WEEKDAYS_FR, "weeks": []}

    last_date = max(by_date.keys())
    # Semaine ISO : lundi -> dimanche. On prend la semaine contenant last_date.
    monday_current = last_date - dt.timedelta(days=last_date.weekday())
    monday_prev    = monday_current - dt.timedelta(days=7)

    def week_block(monday: dt.date) -> list[float | None]:
        return [by_date.get(monday + dt.timedelta(days=i)) for i in range(7)]

    iso_current = monday_current.isocalendar()[1]
    iso_prev    = monday_prev.isocalendar()[1]

    def _fmt_range(mon: dt.date) -> str:
        sun = mon + dt.timedelta(days=6)
        return f"{mon.day:02d}/{mon.month:02d} -> {sun.day:02d}/{sun.month:02d}"

    weeks = [
        {"label": f"Semaine {iso_prev} ({_fmt_range(monday_prev)})",
         "values": week_block(monday_prev)},
        {"label": f"Semaine {iso_current} ({_fmt_range(monday_current)})",
         "values": week_block(monday_current)},
    ]
    return {"xLabels": WEEKDAYS_FR, "weeks": weeks}


# ──────────────────────────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────────────────────────
def main() -> int:
    day_dir = _latest_raw_dir()
    print(f"[INFO] source : {day_dir.relative_to(ROOT)}")

    out: dict = {
        "meta": {
            "generatedAt": dt.datetime.now(dt.timezone.utc)
                                   .isoformat(timespec="seconds")
                                   .replace("+00:00", "Z"),
            "source": "Luminus Business - EPEX Spot (Belpex) / ICIS Heren (TTF DAH)",
            "sourceDir": day_dir.name,
        },
    }

    try:
        out["belpexHourly"] = parse_belpex_hourly(_read_xls(day_dir / "BelpexHourlyCurrent.xls"))
        print(f"[OK]  Belpex horaire : {len(out['belpexHourly']['weeks'])} semaines")
    except Exception as e:
        print(f"[WARN] BelpexHourlyCurrent : {e}", file=sys.stderr)
        out["belpexHourly"] = None

    try:
        out["belpexMonthly"] = parse_monthly_avg(_read_xls(day_dir / "BelpexM_avg.xls"))
        print(f"[OK]  Belpex mensuel  : {len(out['belpexMonthly']['years'])} annees")
    except Exception as e:
        print(f"[WARN] BelpexM_avg : {e}", file=sys.stderr)
        out["belpexMonthly"] = None

    try:
        out["ttfDahDaily"] = parse_ttf_daily(_read_xls(day_dir / "GasTtfDah.xls"))
        print(f"[OK]  TTF DAH journ.  : {len(out['ttfDahDaily']['weeks'])} semaines")
    except Exception as e:
        print(f"[WARN] GasTtfDah : {e}", file=sys.stderr)
        out["ttfDahDaily"] = None

    try:
        out["ttfDahMonthly"] = parse_monthly_avg(_read_xls(day_dir / "GasTtfDahM_avg.xls"))
        print(f"[OK]  TTF DAH mensuel : {len(out['ttfDahMonthly']['years'])} annees")
    except Exception as e:
        print(f"[WARN] GasTtfDahM_avg : {e}", file=sys.stderr)
        out["ttfDahMonthly"] = None

    # Slope Chart : moyennes hebdo Base / Peak / Off-peak (Elec) + Base (Gaz)
    try:
        out["weeklySlope"] = build_weekly_slope(out.get("belpexHourly"), out.get("ttfDahDaily"))
        if out["weeklySlope"]:
            print(f"[OK]  Slope hebdo    : {len(out['weeklySlope']['series'])} series")
    except Exception as e:
        print(f"[WARN] weekly slope : {e}", file=sys.stderr)
        out["weeklySlope"] = None

    OUT_FP.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[DONE] -> {OUT_FP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
