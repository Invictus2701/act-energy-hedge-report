#!/usr/bin/env python3
"""
load_history_xls.py
────────────────────────────────────────────────────────────────────
SEED INITIAL de market_history.json à partir des 6 .xls du dossier
./data. À lancer UNE fois (ou quand les .xls sont rafraîchis).

L'update quotidienne se fait ensuite via scrape_elexys.py qui
UPSERT dans le même fichier market_history.json.

Usage :
  python load_history_xls.py                    # seed + cockpit (asof today)
  python load_history_xls.py --asof 2026-04-15
  python load_history_xls.py --merge            # ne pas écraser, upsert
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

from hedge_core import (
    PREFIX_ELEC, PREFIX_GAS, MONTHS_NAME,
    load_history, save_history, upsert,
    write_cockpit,
)

DATA_DIR = Path(__file__).resolve().parent / "data"

FILES = {
    PREFIX_ELEC: [
        "powerbefwd_month.xls",
        "powerbefwd_qtr.xls",
        "powerbefwd_calall.xls",
    ],
    PREFIX_GAS: [
        "GasTTF_month.xls",
        "GasTTF_qtr.xls",
        "GasTTF_yahall.xls",
    ],
}

MONTHS_UPPER = {m.upper(): i + 1 for i, m in enumerate(MONTHS_NAME)}


def parse_col_to_abs_suffix(col: str) -> str | None:
    """
    MAY2026     -> MONTH|2026|05
    Q3-2026     -> QTR|2026|3
    Cal 2027    -> CAL|2027
    """
    col = str(col).strip()
    m = re.match(r"^([A-Z]{3})(\d{4})$", col.upper())
    if m and m.group(1) in MONTHS_UPPER:
        return f"MONTH|{m.group(2)}|{MONTHS_UPPER[m.group(1)]:02d}"
    m = re.match(r"^Q([1-4])[- ]?(\d{4})$", col, re.I)
    if m:
        return f"QTR|{m.group(2)}|{m.group(1)}"
    m = re.match(r"^Cal[- ]?(\d{4})$", col, re.I)
    if m:
        return f"CAL|{m.group(1)}"
    return None


def load_xls_into(history: dict, fp: Path, prefix: str) -> int:
    df = pd.read_excel(fp, sheet_name="Data")
    df["Quoted Date"] = pd.to_datetime(df["Quoted Date"], dayfirst=True)

    changed = 0
    for col in df.columns:
        if col == "Quoted Date":
            continue
        suffix = parse_col_to_abs_suffix(col)
        if not suffix:
            continue
        code = f"{prefix}|{suffix}"
        for d, v in zip(df["Quoted Date"], df[col]):
            if pd.isna(v):
                continue
            if upsert(history, code, d.date().isoformat(), float(v)):
                changed += 1
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", help="Date d'observation YYYY-MM-DD (défaut: today)")
    ap.add_argument("--merge", action="store_true",
                    help="Upsert dans market_history.json existant (défaut)")
    ap.add_argument("--reset", action="store_true",
                    help="Repartir d'un historique vide")
    args = ap.parse_args()

    asof = dt.date.fromisoformat(args.asof) if args.asof else dt.date.today()

    history = {} if args.reset else load_history()
    print(f"[INFO] Historique initial : {len(history)} contrats")

    total_changes = 0
    for prefix, files in FILES.items():
        for name in files:
            fp = DATA_DIR / name
            if not fp.exists():
                print(f"[WARN] manquant : {fp}", file=sys.stderr)
                continue
            changes = load_xls_into(history, fp, prefix)
            total_changes += changes
            print(f"[OK]  {name}: {changes} points upsert")

    save_history(history)
    print(f"[SAVE] market_history.json ({len(history)} contrats, {total_changes} updates)")

    write_cockpit(history, asof, "Historical XLS seed (data/*.xls)")
    print(f"[SAVE] statistics-data.json (asof={asof})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
