#!/usr/bin/env python3
"""
process_data.py
────────────────────────────────────────────────────────────────────
Normalise les rapports Excel téléchargés par fetch_luminus.py et
produit deux artefacts JSON consommés par le frontend Cockpit :

  data/master_history.json
      { product_code: { "YYYY-MM-DD": settlement_price, ... }, ... }
      Série quotidienne fusionnée depuis le 01/01/2026 pour les
      12 produits clés (BE Power × {M1,Q1,Q2,Y1,Y2,Y3} +
                       TTF Gas   × {M1,Q1,Q2,Y1,Y2,Y3}).

  data/statistics-data.json
      Bloc Cockpit prêt à consommer : Var D-1, Var W-1, YTD Avg/Max/Min,
      6 dernières sessions par produit.

Entrée :
  data/raw/YYYY-MM-DD/{power|gas}_{month|quarter|years|spot}.xlsx
  (8 fichiers/jour, produits par fetch_luminus.py)

Validation :
  Le script vérifie au 2026-04-14 que :
      BE_POWER_BASE_Y1 = 84.37
      BE_POWER_BASE_M1 = 83.04
      TTF_NG_Y1        = 34.74
      TTF_NG_M1        = 43.37
  Tolérance par défaut : ±0.5 %. Échec → exit code 2.

Usage :
  python scripts/process_data.py             # ingère uniquement aujourd'hui
  python scripts/process_data.py --all       # rejoue tout data/raw/
  python scripts/process_data.py --date 2026-04-14
  python scripts/process_data.py --validate-only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

# ──────────────────────────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parents[1]
RAW_DIR    = ROOT / "data" / "raw"
DATA_DIR   = ROOT / "data"
HISTORY_FP = DATA_DIR / "master_history.json"
COCKPIT_FP = DATA_DIR / "statistics-data.json"

YTD_START = dt.date(2026, 1, 1)

MONTHS = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
          "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}

# Fichier Excel → groupe (ELECTRICITY/GAS). Plusieurs noms possibles
# pour un même contenu (le scraper peut sauvegarder en slug propre, mais
# le téléchargement direct depuis Luminus garde le nom natif).
FILE_GROUPS: dict[str, str] = {
    # noms natifs Luminus
    "powerbefwd_month":   "ELECTRICITY",
    "powerbefwd_qtr":     "ELECTRICITY",
    "powerbefwd_calall":  "ELECTRICITY",
    "powerbefwd_cal":     "ELECTRICITY",
    "powerbefwd_yah":     "ELECTRICITY",
    "GasTTF_month":       "GAS",
    "GasTTF_qtr":         "GAS",
    "GasTTF_yahall":      "GAS",
    "GasTTF_yah":         "GAS",
    # slugs canoniques (au cas où le scraper renomme)
    "power_month":        "ELECTRICITY",
    "power_quarter":      "ELECTRICITY",
    "power_years":        "ELECTRICITY",
    "gas_month":          "GAS",
    "gas_quarter":        "GAS",
    "gas_years":          "GAS",
}

# 18 codes produits stockes dans master_history.json (9 tenors x 2 groupes).
# Les graphiques consomment l'ensemble ; le tableau Statistics ne prend
# que les 12 produits listes dans STATS_TENORS (ci-dessous).
CODES_BY_GROUP = {
    "ELECTRICITY": {
        "M1": "BE_POWER_BASE_M1", "M2": "BE_POWER_BASE_M2", "M3": "BE_POWER_BASE_M3",
        "Q1": "BE_POWER_BASE_Q1", "Q2": "BE_POWER_BASE_Q2", "Q3": "BE_POWER_BASE_Q3",
        "Y1": "BE_POWER_BASE_Y1", "Y2": "BE_POWER_BASE_Y2", "Y3": "BE_POWER_BASE_Y3",
    },
    "GAS": {
        "M1": "TTF_NG_M1", "M2": "TTF_NG_M2", "M3": "TTF_NG_M3",
        "Q1": "TTF_NG_Q1", "Q2": "TTF_NG_Q2", "Q3": "TTF_NG_Q3",
        "Y1": "TTF_NG_Y1", "Y2": "TTF_NG_Y2", "Y3": "TTF_NG_Y3",
    },
}

# Sous-ensemble affiche dans le tableau Statistics (12 produits).
STATS_TENORS = ("M1", "Q1", "Q2", "Y1", "Y2", "Y3")

PRODUCT_LABELS = {
    "BE_POWER_BASE_M1": "BE M+1 base",
    "BE_POWER_BASE_M2": "BE M+2 base",
    "BE_POWER_BASE_M3": "BE M+3 base",
    "BE_POWER_BASE_Q1": "BE T+1 base",
    "BE_POWER_BASE_Q2": "BE T+2 base",
    "BE_POWER_BASE_Q3": "BE T+3 base",
    "BE_POWER_BASE_Y1": "BE A+1 base",
    "BE_POWER_BASE_Y2": "BE A+2 base",
    "BE_POWER_BASE_Y3": "BE A+3 base",
    "TTF_NG_M1": "TTF M+1",
    "TTF_NG_M2": "TTF M+2",
    "TTF_NG_M3": "TTF M+3",
    "TTF_NG_Q1": "TTF T+1",
    "TTF_NG_Q2": "TTF T+2",
    "TTF_NG_Q3": "TTF T+3",
    "TTF_NG_Y1": "TTF A+1",
    "TTF_NG_Y2": "TTF A+2",
    "TTF_NG_Y3": "TTF A+3",
}

# Traduction des jours de la semaine (strftime("%A") depend de la locale OS,
# on fige en francais pour garantir la coherence entre Windows / Linux CI).
WEEKDAYS_FR = {
    "Monday":    "Lundi",
    "Tuesday":   "Mardi",
    "Wednesday": "Mercredi",
    "Thursday":  "Jeudi",
    "Friday":    "Vendredi",
    "Saturday":  "Samedi",
    "Sunday":    "Dimanche",
}

# Benchmark de validation (cf. brief)
VALIDATION_BENCHMARK: dict[str, dict[str, float]] = {
    "2026-04-14": {
        "BE_POWER_BASE_Y1": 84.37,
        "BE_POWER_BASE_M1": 83.04,
        "TTF_NG_Y1":        34.74,
        "TTF_NG_M1":        43.37,
    },
}
VALIDATION_TOLERANCE = 0.005  # 0.5 %


# ──────────────────────────────────────────────────────────────────
#  Parsing helpers
# ──────────────────────────────────────────────────────────────────
def classify_tenor(label: str, observation: dt.date) -> str | None:
    """Convertit un libellé contrat ('May-26', 'Q3-26', 'Cal-27') en tenor
    (M1..M3 / Q1..Q3 / Y1..Y3) relatif à la date d'observation. Retourne
    None si hors périmètre."""
    p = str(label).strip()
    y2 = observation.year % 100

    m = re.match(r"^Cal[-\s]?(\d{2,4})$", p, re.I)
    if m:
        yy = int(m.group(1)) % 100
        diff = yy - y2
        return f"Y{diff}" if 1 <= diff <= 3 else None

    m = re.match(r"^Q([1-4])[-\s]?(\d{2,4})$", p, re.I)
    if m:
        q, yy = int(m.group(1)), int(m.group(2)) % 100
        q_now = (observation.month - 1) // 3 + 1
        diff_q = (yy - y2) * 4 + (q - q_now)
        return f"Q{diff_q}" if 1 <= diff_q <= 3 else None

    m = re.match(r"^([A-Za-z]{3})[-\s]?(\d{2,4})$", p)
    if m and m.group(1)[:3].lower() in MONTHS:
        mm = MONTHS[m.group(1)[:3].lower()]
        yy = int(m.group(2)) % 100
        diff_m = (yy - y2) * 12 + (mm - observation.month)
        return f"M{diff_m}" if 1 <= diff_m <= 3 else None

    return None


def _coerce_price(raw) -> float | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, (int, float)):
        v = float(raw)
    else:
        s = str(raw).strip().replace("€", "").replace("\xa0", "").replace(" ", "")
        s = s.replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            return None
    if not (0 < v < 10_000):
        return None
    return v


def _coerce_date(raw) -> dt.date | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, dt.datetime):
        return raw.date()
    if isinstance(raw, dt.date):
        return raw
    try:
        return pd.to_datetime(raw, dayfirst=True, errors="coerce").date()
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────
#  Excel extraction
# ──────────────────────────────────────────────────────────────────
def _read_excel_any(path: Path) -> dict[str, pd.DataFrame]:
    """Lit un .xls (xlrd) ou .xlsx (openpyxl) en autodétectant le moteur."""
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    return pd.read_excel(path, sheet_name=None, header=None, engine=engine)


def extract_from_excel(path: Path, group: str) -> list[tuple[dt.date, str, float]]:
    """Ouvre un Excel Luminus et renvoie une liste de tuples
    (settlement_date, tenor_code, price) — uniquement pour les tenors
    M1/Q1/Q2/Y1/Y2/Y3 du groupe demandé.

    Format observé :
      - Ligne d'en-tête = ['Quoted Date', '<contract1>', '<contract2>', ...]
      - Lignes suivantes = date dans la 1re colonne, prix sous chaque contrat.
      - Libellés contrats : 'Cal 2027', 'MAY2026', 'Q1-2027' (4 chiffres pour
        l'année).
    """
    rows: list[tuple[dt.date, str, float]] = []
    try:
        sheets = _read_excel_any(path)
    except Exception as exc:
        print(f"[WARN] {path.name}: lecture impossible ({exc})", file=sys.stderr)
        return rows

    for _, df in sheets.items():
        if df.empty:
            continue
        rows.extend(_extract_timeseries(df, group))

    # Déduplique (même date+tenor → garde la dernière valeur rencontrée)
    seen: dict[tuple[dt.date, str], float] = {}
    for d, t, p in rows:
        seen[(d, t)] = p
    return [(d, t, p) for (d, t), p in seen.items()]


def _extract_timeseries(df: pd.DataFrame, group: str) -> list[tuple[dt.date, str, float]]:
    """Format Luminus : header = ['Quoted Date', <contract>, <contract>, …].
    La date est en colonne 0 ; chaque cellule (date, contract) est un prix
    de settlement. Le tenor (M1/Q1/Q2/Y1/Y2/Y3) est calculé relativement
    à la date de la ligne (pas à la date de génération du fichier)."""
    out: list[tuple[dt.date, str, float]] = []
    targets = set(CODES_BY_GROUP[group].keys())

    # Détection de la ligne d'en-tête : col 0 contient "Quoted Date".
    header_row = None
    for i in range(min(8, len(df))):
        cell = df.iat[i, 0]
        if cell is None:
            continue
        text = str(cell).strip().lower()
        if "quoted" in text and "date" in text:
            header_row = i
            break
    if header_row is None:
        return out

    headers = df.iloc[header_row].tolist()
    body    = df.iloc[header_row + 1 :].reset_index(drop=True)

    for _, row in body.iterrows():
        d = _coerce_date(row.iat[0])
        if d is None or d < YTD_START:
            continue
        for j in range(1, len(headers)):
            label = headers[j]
            if label is None or (isinstance(label, float) and pd.isna(label)):
                continue
            tenor = classify_tenor(label, d)
            if tenor not in targets:
                continue
            price = _coerce_price(row.iat[j])
            if price is None:
                continue
            out.append((d, tenor, price))
    return out


# ──────────────────────────────────────────────────────────────────
#  History merge
# ──────────────────────────────────────────────────────────────────
def load_history() -> dict[str, dict[str, float]]:
    if HISTORY_FP.exists():
        return json.loads(HISTORY_FP.read_text("utf-8"))
    return {}


def save_history(history: dict[str, dict[str, float]]) -> None:
    HISTORY_FP.parent.mkdir(parents=True, exist_ok=True)
    # Tri par produit puis par date pour un diff git lisible.
    ordered = {p: dict(sorted(series.items())) for p, series in sorted(history.items())}
    HISTORY_FP.write_text(json.dumps(ordered, indent=2), "utf-8")


def ingest_day(history: dict[str, dict[str, float]], day_dir: Path) -> int:
    """Met à jour history avec les Excel d'un dossier YYYY-MM-DD."""
    try:
        day = dt.date.fromisoformat(day_dir.name)
    except ValueError:
        print(f"[WARN] dossier ignoré (nom non-date): {day_dir}", file=sys.stderr)
        return 0
    if day < YTD_START:
        return 0

    inserted = 0
    # Itère tous les fichiers Excel du dossier, en mappant nom → groupe.
    for path in sorted(day_dir.iterdir()):
        if path.suffix.lower() not in (".xls", ".xlsx"):
            continue
        group = FILE_GROUPS.get(path.stem)
        if group is None:
            print(f"[WARN] fichier inconnu ignoré : {path.name}", file=sys.stderr)
            continue
        for d, tenor, price in extract_from_excel(path, group):
            code = CODES_BY_GROUP[group][tenor]
            history.setdefault(code, {})[d.isoformat()] = round(price, 4)
            inserted += 1
    return inserted


# ──────────────────────────────────────────────────────────────────
#  Statistics
# ──────────────────────────────────────────────────────────────────
def _last_business_days(n: int, upto: dt.date) -> list[dt.date]:
    days, d = [], upto
    while len(days) < n:
        if d.weekday() < 5:
            days.insert(0, d)
        d -= dt.timedelta(days=1)
    return days


def _pct(numer: float, denom: float) -> float | None:
    if denom in (0, None):
        return None
    return round((numer - denom) / denom * 100, 2)


def _last_data_date(history: dict[str, dict[str, float]]) -> dt.date | None:
    """Trouve la derniere date pour laquelle au moins un produit a un prix."""
    latest = None
    for series in history.values():
        for d_iso in series:
            d = dt.date.fromisoformat(d_iso)
            if latest is None or d > latest:
                latest = d
    return latest


def build_statistics(history: dict[str, dict[str, float]], today: dt.date) -> dict:
    # Ancre les sessions sur la derniere date avec des donnees, pas sur
    # aujourd'hui (evite une colonne vide si le settlement du jour n'est
    # pas encore publie).
    anchor = _last_data_date(history) or today
    sessions_d = _last_business_days(6, anchor)
    sessions = [{
        "label":   f"{d.day}/{d.month}",
        "weekday": WEEKDAYS_FR.get(d.strftime("%A"), d.strftime("%A")),
        "date":    d.isoformat(),
    } for d in sessions_d]
    ytd_iso = YTD_START.isoformat()

    def product_block(code: str) -> dict:
        series = history.get(code, {})
        prices = [series.get(d.isoformat()) for d in sessions_d]

        sorted_days = sorted(series.keys())
        var_d1 = var_w1 = None
        last = series[sorted_days[-1]] if sorted_days else None

        if len(sorted_days) >= 2 and last is not None:
            var_d1 = _pct(last, series[sorted_days[-2]])

        if last is not None and sorted_days:
            anchor = dt.date.fromisoformat(sorted_days[-1])
            target = anchor - dt.timedelta(days=7)
            ref = series.get(target.isoformat())
            if ref is None:
                for delta in (1, -1, 2, -2, 3, -3):
                    ref = series.get((target + dt.timedelta(days=delta)).isoformat())
                    if ref is not None:
                        break
            if ref:
                var_w1 = _pct(last, ref)

        ytd = [v for k, v in series.items() if k >= ytd_iso and v is not None]
        avg = round(sum(ytd) / len(ytd), 2) if ytd else None
        mx  = round(max(ytd), 2) if ytd else None
        mn  = round(min(ytd), 2) if ytd else None

        return {
            "code": code, "label": PRODUCT_LABELS[code],
            "prices": [round(p, 2) if p is not None else None for p in prices],
            "varD1": var_d1, "varW1": var_w1,
            "avg": avg, "max": mx, "min": mn,
        }

    electricity = [product_block(CODES_BY_GROUP["ELECTRICITY"][t]) for t in STATS_TENORS]
    gas         = [product_block(CODES_BY_GROUP["GAS"][t]) for t in STATS_TENORS]

    return {
        "meta": {
            "module": "Statistiques",
            "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "source": "Luminus Business — https://my.luminusbusiness.be/market-info/",
            "currency": "EUR", "unit": "MWh",
            "ytdStart": ytd_iso,
            "sessions": sessions,
        },
        "markets": [
            {"group": "ELECTRICITY", "products": electricity},
            {"group": "GAS",         "products": gas},
        ],
    }


# ──────────────────────────────────────────────────────────────────
#  Validation
# ──────────────────────────────────────────────────────────────────
def validate(history: dict[str, dict[str, float]]) -> list[str]:
    errors: list[str] = []
    for day_iso, expected in VALIDATION_BENCHMARK.items():
        for code, ref in expected.items():
            actual = history.get(code, {}).get(day_iso)
            if actual is None:
                errors.append(f"{day_iso} {code}: manquant (attendu {ref})")
                continue
            if abs(actual - ref) / ref > VALIDATION_TOLERANCE:
                errors.append(
                    f"{day_iso} {code}: lu {actual:.4f}, attendu {ref:.4f} "
                    f"(écart {(actual-ref)/ref*100:+.2f} %)"
                )
    return errors


# ──────────────────────────────────────────────────────────────────
#  Orchestration
# ──────────────────────────────────────────────────────────────────
def discover_day_dirs(scope: str, only: dt.date | None) -> list[Path]:
    if not RAW_DIR.exists():
        return []
    if only is not None:
        d = RAW_DIR / only.isoformat()
        return [d] if d.exists() else []
    if scope == "all":
        return sorted(p for p in RAW_DIR.iterdir() if p.is_dir())
    # scope == "today"
    d = RAW_DIR / dt.date.today().isoformat()
    return [d] if d.exists() else []


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalise les Excel Luminus en JSON Cockpit.")
    p.add_argument("--all", action="store_true", help="Rejoue tout data/raw/.")
    p.add_argument("--date", type=dt.date.fromisoformat, default=None,
                   help="Ne traiter que cette date (YYYY-MM-DD).")
    p.add_argument("--validate-only", action="store_true",
                   help="Recharge l'historique existant et lance les checks.")
    p.add_argument("--strict-validation", action="store_true",
                   help="Échec (exit 2) si la validation benchmark ne passe pas.")
    return p.parse_args(list(argv))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    history = load_history()

    if not args.validate_only:
        scope = "all" if args.all else "today"
        day_dirs = discover_day_dirs(scope, args.date)
        if not day_dirs:
            print("[WARN] aucun dossier raw à ingérer.", file=sys.stderr)
        total_inserted = 0
        for d in day_dirs:
            inserted = ingest_day(history, d)
            print(f"[OK]  ingere {inserted:>4} points depuis {d.relative_to(ROOT)}")
            total_inserted += inserted
        save_history(history)

        cockpit = build_statistics(history, dt.date.today())
        COCKPIT_FP.write_text(json.dumps(cockpit, indent=2), "utf-8")
        print(f"[DONE] {total_inserted} points ingeres. "
              f"-> {HISTORY_FP.relative_to(ROOT)}, {COCKPIT_FP.relative_to(ROOT)}")

    errors = validate(history)
    if errors:
        print("\n[VALIDATION] echecs :", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        if args.strict_validation or args.validate_only:
            return 2
    else:
        print("[VALIDATION] OK - benchmark 2026-04-14 conforme.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
