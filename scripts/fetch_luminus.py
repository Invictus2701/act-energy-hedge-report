#!/usr/bin/env python3
"""
fetch_luminus.py
────────────────────────────────────────────────────────────────────
Telecharge les 12 rapports Excel (Forward + Spot) depuis le portail
public Luminus Business Market Info.

Les fichiers sont de simples liens directs :
  https://my.luminusbusiness.be/market-info/downloads/<filename>.xls

Aucune authentification, aucun JavaScript, aucun navigateur requis.

Sortie :
  data/raw/YYYY-MM-DD/<filename>.xls

Usage :
  python scripts/fetch_luminus.py                # telecharge pour aujourd'hui
  python scripts/fetch_luminus.py --date 2026-04-16
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import requests

# ──────────────────────────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
BASE    = "https://my.luminusbusiness.be/market-info/downloads"

# Les 12 rapports utilises par le Cockpit + Hedge Report.
# Cle = nom du fichier sur le serveur (sans extension).
REPORTS: dict[str, str] = {
    # Forward Electricite (BE Power)
    "powerbefwd_month":  "Power Forward Monthly",
    "powerbefwd_qtr":    "Power Forward Quarterly",
    "powerbefwd_calall": "Power Forward Yearly (all)",
    "powerbefwd_cal":    "Power Forward Yearly (12M)",
    # Forward Gaz (TTF)
    "GasTTF_month":      "Gas Forward Monthly",
    "GasTTF_qtr":        "Gas Forward Quarterly",
    "GasTTF_yahall":     "Gas Forward Yearly (all)",
    "GasTTF_yah":        "Gas Forward Yearly (12M)",
    # Spot Electricite (Belpex)
    "BelpexHourlyCurrent": "Power Spot Hourly",
    "BelpexM_avg":         "Power Spot Monthly Avg",
    # Spot Gaz (TTF Day-Ahead)
    "GasTtfDah":           "Gas Spot DAH",
    "GasTtfDahM_avg":      "Gas Spot DAH Monthly Avg",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


# ──────────────────────────────────────────────────────────────────
#  Download
# ──────────────────────────────────────────────────────────────────
def download_file(filename: str, label: str, out_dir: Path) -> Path | None:
    url  = f"{BASE}/{filename}.xls"
    dest = out_dir / f"{filename}.xls"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        size_kb = len(r.content) / 1024
        print(f"[OK]  {label:<26s} -> {dest.name} ({size_kb:.0f} KB)")
        return dest
    except Exception as exc:
        print(f"[WARN] {label}: {exc}", file=sys.stderr)
        return None


def fetch_all(target_date: dt.date) -> list[Path]:
    out_dir = RAW_DIR / target_date.isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for filename, label in REPORTS.items():
        result = download_file(filename, label, out_dir)
        if result:
            saved.append(result)

    total = len(REPORTS)
    if len(saved) == total:
        print(f"[DONE] {len(saved)}/{total} rapports dans {out_dir.relative_to(ROOT)}")
    else:
        print(
            f"[WARN] {len(saved)}/{total} rapports telecharges.",
            file=sys.stderr,
        )
    return saved


# ──────────────────────────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────────────────────────
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Telecharge les 12 rapports Forward + Spot Luminus Business."
    )
    p.add_argument(
        "--date",
        type=dt.date.fromisoformat,
        default=dt.date.today(),
        help="Date cible (YYYY-MM-DD). Par defaut : aujourd'hui.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    saved = fetch_all(args.date)
    return 0 if len(saved) == len(REPORTS) else 1


if __name__ == "__main__":
    sys.exit(main())
