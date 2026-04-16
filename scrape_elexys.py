#\!/usr/bin/env python3
"""
scrape_elexys.py
Mise a jour quotidienne de market_history.json depuis les pages
publiques Elexys (nouvelle version du site, avril 2026) :
  https://www.elexys.be/en/insights/ice-endex-belgian-power-base
  https://www.elexys.be/en/insights/ice-endex-dutch-natural-gas-forward

Usage :
  python scrape_elexys.py              # fetch + upsert + cockpit
  python scrape_elexys.py --dry-run    # fetch + affiche, n ecrit pas
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from hedge_core import (
    PREFIX_ELEC, PREFIX_GAS,
    load_history, save_history, upsert,
    write_cockpit,
)

URLS = {
    PREFIX_ELEC: "https://www.elexys.be/en/insights/ice-endex-belgian-power-base",
    PREFIX_GAS:  "https://www.elexys.be/en/insights/ice-endex-dutch-natural-gas-forward",
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9,fr-BE;q=0.8,fr;q=0.7",
    "Referer": "https://www.elexys.be/",
}

MONTHS = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
          "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}


def elexys_label_to_abs_suffix(label):
    p = label.strip()
    m = re.match(r"^Cal[- ]?(\d{2})$", p, re.I)
    if m:
        return "CAL|20" + m.group(1)
    m = re.match(r"^Q([1-4])[- ]?(\d{2})$", p, re.I)
    if m:
        return "QTR|20" + m.group(2) + "|" + m.group(1)
    m = re.match(r"^([A-Za-z]{3})[- ]?(\d{2})$", p)
    if m and m.group(1).title() in MONTHS:
        mm = MONTHS[m.group(1).title()]
        return "MONTH|20" + m.group(2) + "|" + str(mm).zfill(2)
    return None


def prev_business_day(d):
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d = d - dt.timedelta(days=1)
    return d


def parse_euro(raw):
    cleaned = raw.replace("\u20ac", "").replace("\u00a0", "").replace(",", ".").strip()
    try:
        val = float(cleaned)
        return val if 0 < val < 10000 else None
    except ValueError:
        return None


def parse_elexys_page(html, today):
    soup = BeautifulSoup(html, "html.parser")
    settle_date = prev_business_day(today)
    text = soup.get_text(" ", strip=True)

    m = re.search(r"Last quotation:\s*(\d{2})-(\d{2})-(\d{4})", text)
    if m:
        pub_date = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        settle_date = prev_business_day(pub_date)
    else:
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text)
        if m:
            pub_date = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            settle_date = prev_business_day(pub_date)

    rows = []
    for table in soup.find_all("table", class_="c-table-insights"):
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            suffix = elexys_label_to_abs_suffix(cells[0])
            if not suffix:
                continue
            price = parse_euro(cells[1])
            if price is not None:
                rows.append((suffix, price))
    return rows, settle_date


def fetch_group(prefix):
    url = URLS[prefix]
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return parse_elexys_page(r.text, dt.date.today())
        except Exception as e:
            print("[WARN] %s attempt %d: %s" % (prefix, attempt+1, e), file=sys.stderr)
            time.sleep(2 + attempt * 3)
    raise RuntimeError("Unable to scrape %s from %s" % (prefix, url))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="N ecrit rien, affiche simplement les valeurs scrapees")
    args = ap.parse_args()

    history = load_history()
    today = dt.date.today()
    print("[INFO] Historique courant : %d contrats" % len(history))

    total_upsert = 0
    for prefix in (PREFIX_ELEC, PREFIX_GAS):
        rows, settle = fetch_group(prefix)
        print("[OK] %s settlement %s : %d contrats scrapes" % (prefix, settle, len(rows)))

        for suffix, value in rows:
            code = prefix + "|" + suffix
            if args.dry_run:
                print("   [DRY] %s @ %s = %s" % (code, settle, value))
                continue
            if upsert(history, code, settle.isoformat(), value):
                total_upsert += 1

    if args.dry_run:
        print("[DRY] aucun fichier modifie")
        return 0

    save_history(history)
    print("[SAVE] market_history.json (+%d points mis a jour)" % total_upsert)

    write_cockpit(history, today, "Elexys daily scrape + XLS history")
    print("[SAVE] statistics-data.json + .js (asof=%s)" % today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
