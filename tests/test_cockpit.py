"""
Suite de tests pour le pipeline Elexys -> Cockpit.

Couvre les 5 axes :
  1. Précision des données (valeurs de référence 14/04/2026)
  2. Robustesse (encodage, HTML cassé, retry 503)
  3. Logique métier (Var D-1, Var W-1 fallback, YTD)
  4. CI/CD (YAML + TZ + cron)
  5. Persistance (upsert + intégrité JSON)
"""
from __future__ import annotations
import datetime as dt
import io, json, sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scrape_elexys as se  # noqa: E402

REF_DATE = dt.date(2026, 4, 14)

# ──────────────────────────────────────────────────────────────────
#  Fixtures HTML (reproduisent le format tabulaire Elexys)
# ──────────────────────────────────────────────────────────────────
ELEC_HTML = """
<html><body>
<h2>Endex Power Belgium — Settlement 14/04/2026</h2>
<table id="endex">
  <tr><th>Product</th><th>Settlement</th></tr>
  <tr><td>May-26</td> <td>83,04</td></tr>
  <tr><td>Q3-26</td>  <td>92,50</td></tr>
  <tr><td>Q4-26</td>  <td>101,43</td></tr>
  <tr><td>Cal-27</td> <td>84,37</td></tr>
  <tr><td>Cal-28</td> <td>73,63</td></tr>
  <tr><td>Cal-29</td> <td>71,11</td></tr>
</table></body></html>
"""

GAS_HTML = """
<html><body>
<h2>TTF Natural Gas — Settlement 14/04/2026</h2>
<table id="ttf">
  <tr><th>Product</th><th>Settlement</th></tr>
  <tr><td>May-26</td> <td>43,37</td></tr>
  <tr><td>Q3-26</td>  <td>43,02</td></tr>
  <tr><td>Q4-26</td>  <td>42,49</td></tr>
  <tr><td>Cal-27</td> <td>34,74</td></tr>
  <tr><td>Cal-28</td> <td>26,70</td></tr>
  <tr><td>Cal-29</td> <td>23,75</td></tr>
</table></body></html>
"""

def _mk_response(text: str, status: int = 200, encoding: str = "utf-8"):
    r = SimpleNamespace()
    r.status_code = status
    r.encoding = encoding
    r.text = text if isinstance(text, str) else text.decode(encoding)
    def _raise():
        if status >= 400:
            import requests
            raise requests.HTTPError(f"{status}")
    r.raise_for_status = _raise
    return r

# ══════════════════════════════════════════════════════════════════
#  1. Précision des données
# ══════════════════════════════════════════════════════════════════
class TestDataAccuracy:
    def test_electricity_values(self):
        prices, date = se.parse_elexys_table(ELEC_HTML, REF_DATE)
        assert date == REF_DATE
        assert prices["M1"] == 83.04
        assert prices["Y1"] == 84.37   # BE Y+1 base
        assert prices["Q1"] == 92.50
        assert prices["Q2"] == 101.43
        assert prices["Y2"] == 73.63
        assert prices["Y3"] == 71.11

    def test_gas_values(self):
        prices, _ = se.parse_elexys_table(GAS_HTML, REF_DATE)
        assert prices["M1"] == 43.37   # TTF M+1
        assert prices["Y1"] == 34.74   # TTF Y+1
        assert prices["Q1"] == 43.02
        assert prices["Q2"] == 42.49

    def test_mapping_to_cockpit_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(se, "HISTORY_FP", tmp_path / "hist.json")
        monkeypatch.setattr(se, "COCKPIT_FP", tmp_path / "cockpit.json")
        hist = {
            "BE_POWER_BASE_M1": {REF_DATE.isoformat(): 83.04},
            "BE_POWER_BASE_Y1": {REF_DATE.isoformat(): 84.37},
            "TTF_NG_M1":        {REF_DATE.isoformat(): 43.37},
            "TTF_NG_Y1":        {REF_DATE.isoformat(): 34.74},
        }
        cockpit = se.build_cockpit(hist, REF_DATE)
        elec = {p["code"]: p for p in cockpit["markets"][0]["products"]}
        gas  = {p["code"]: p for p in cockpit["markets"][1]["products"]}
        assert elec["BE_POWER_BASE_M1"]["prices"][-1] == 83.04
        assert elec["BE_POWER_BASE_Y1"]["prices"][-1] == 84.37
        assert gas["TTF_NG_M1"]["prices"][-1] == 43.37
        assert gas["TTF_NG_Y1"]["prices"][-1] == 34.74

# ══════════════════════════════════════════════════════════════════
#  2. Robustesse
# ══════════════════════════════════════════════════════════════════
class TestRobustness:
    def test_iso_8859_1_encoding(self):
        # Fixture minimale 100% latin-1 avec accents (Fédération / Électricité)
        html = (
            "<html><body><h2>Fédération Électricité</h2>"
            "<table><tr><th>Product</th><th>Settlement</th></tr>"
            "<tr><td>May-26</td><td>83,04</td></tr>"
            "<tr><td>Cal-27</td><td>84,37</td></tr>"
            "</table></body></html>"
        )
        raw = html.encode("iso-8859-1")       # ne doit pas crasher
        prices, _ = se.parse_elexys_table(raw.decode("iso-8859-1"), REF_DATE)
        assert prices["M1"] == 83.04
        assert prices["Y1"] == 84.37

    def test_broken_html_returns_empty_not_crash(self):
        # Pas de <table> : doit renvoyer {} sans AttributeError
        prices, _ = se.parse_elexys_table("<html><body>oops</body></html>", REF_DATE)
        assert prices == {}

    def test_retry_on_503(self, monkeypatch):
        calls = {"n": 0}
        def fake_get(url, headers=None, timeout=None):
            calls["n"] += 1
            if calls["n"] < 3:
                return _mk_response("", status=503)
            return _mk_response(ELEC_HTML)
        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        monkeypatch.setattr(se.time, "sleep", lambda *_: None)
        prices, _ = se.fetch_group("ELECTRICITY")
        assert calls["n"] == 3          # 2 échecs + 1 succès
        assert prices["Y1"] == 84.37

    def test_retry_gives_up_after_3(self, monkeypatch):
        def fake_get(*a, **kw):
            return _mk_response("", status=503)
        import requests
        monkeypatch.setattr(requests, "get", fake_get)
        monkeypatch.setattr(se.time, "sleep", lambda *_: None)
        with pytest.raises(RuntimeError, match="Unable to scrape"):
            se.fetch_group("GAS")

# ══════════════════════════════════════════════════════════════════
#  3. Logique métier
# ══════════════════════════════════════════════════════════════════
class TestBusinessLogic:
    def _hist(self, series):
        return {"BE_POWER_BASE_Y1": dict(series)}

    def test_var_d1_exact(self):
        # J-1 = 100.00 ; J = 95.00 -> -5.00%
        hist = self._hist({
            "2026-04-13": 100.00,
            "2026-04-14": 95.00,
        })
        cockpit = se.build_cockpit(hist, REF_DATE)
        y1 = next(p for p in cockpit["markets"][0]["products"]
                  if p["code"] == "BE_POWER_BASE_Y1")
        assert y1["varD1"] == -5.00

    def test_var_w1_fallback_to_j6(self):
        # J = 2026-04-14, J-7 = 2026-04-07 ABSENT ; J-6 = 2026-04-08 présent
        hist = self._hist({
            "2026-04-08": 90.00,   # fallback (J-6)
            "2026-04-13": 94.00,
            "2026-04-14": 99.00,
        })
        cockpit = se.build_cockpit(hist, REF_DATE)
        y1 = next(p for p in cockpit["markets"][0]["products"]
                  if p["code"] == "BE_POWER_BASE_Y1")
        # (99 - 90) / 90 * 100 = 10.00
        assert y1["varW1"] == 10.00

    def test_ytd_stats_include_today(self):
        hist = self._hist({
            "2026-01-05": 70.00,
            "2026-02-10": 100.00,   # max
            "2026-03-15": 60.00,    # min
            "2026-04-14": 84.37,
        })
        cockpit = se.build_cockpit(hist, REF_DATE)
        y1 = next(p for p in cockpit["markets"][0]["products"]
                  if p["code"] == "BE_POWER_BASE_Y1")
        assert y1["max"] == 100.00
        assert y1["min"] == 60.00
        # moyenne = (70 + 100 + 60 + 84.37) / 4 = 78.5925 -> 78.59
        assert y1["avg"] == 78.59

# ══════════════════════════════════════════════════════════════════
#  4. CI/CD
# ══════════════════════════════════════════════════════════════════
class TestWorkflow:
    WF = ROOT / ".github" / "workflows" / "daily_update.yml"

    def test_yaml_is_valid(self):
        import yaml
        doc = yaml.safe_load(self.WF.read_text("utf-8"))
        assert "jobs" in doc
        assert "scrape" in doc["jobs"]

    def test_has_write_permission(self):
        txt = self.WF.read_text("utf-8")
        assert "contents: write" in txt
        assert "workflow_dispatch" in txt

    def test_tz_brussels_and_cron(self):
        txt = self.WF.read_text("utf-8")
        assert 'TZ="Europe/Brussels"' in txt or "TZ=Europe/Brussels" in txt
        # Cron doublon pour couvrir CET (18 UTC) et CEST (19 UTC)
        assert '"0 18 * * 1-5"' in txt
        assert '"0 19 * * 1-5"' in txt

# ══════════════════════════════════════════════════════════════════
#  5. Persistance
# ══════════════════════════════════════════════════════════════════
class TestPersistence:
    def test_upsert_no_duplicates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(se, "HISTORY_FP", tmp_path / "hist.json")
        monkeypatch.setattr(se, "COCKPIT_FP", tmp_path / "cockpit.json")

        # Seed
        hist = {"BE_POWER_BASE_M1": {REF_DATE.isoformat(): 83.04}}
        se.save_history(hist)
        # Second run même date, même prix -> toujours une seule clé
        h2 = se.load_history()
        h2.setdefault("BE_POWER_BASE_M1", {})[REF_DATE.isoformat()] = 83.04
        se.save_history(h2)

        final = json.loads((tmp_path / "hist.json").read_text("utf-8"))
        keys = list(final["BE_POWER_BASE_M1"].keys())
        assert keys.count(REF_DATE.isoformat()) == 1
        assert len(keys) == 1

    def test_cockpit_json_integrity(self, tmp_path, monkeypatch):
        monkeypatch.setattr(se, "HISTORY_FP", tmp_path / "hist.json")
        monkeypatch.setattr(se, "COCKPIT_FP", tmp_path / "cockpit.json")
        hist = {"BE_POWER_BASE_Y1": {REF_DATE.isoformat(): 84.37}}
        cockpit = se.build_cockpit(hist, REF_DATE)
        out = tmp_path / "cockpit.json"
        out.write_text(json.dumps(cockpit), "utf-8")

        reloaded = json.loads(out.read_text("utf-8"))
        # Syntaxe OK + 6 sessions
        assert len(reloaded["meta"]["sessions"]) == 6
        # Structure markets[2] avec 6 produits chacun
        assert len(reloaded["markets"]) == 2
        for grp in reloaded["markets"]:
            assert len(grp["products"]) == 6
