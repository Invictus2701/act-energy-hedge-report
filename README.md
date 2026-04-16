# ACT Energy — Hedge Report

Dashboard de suivi des prix de marché de l'énergie (électricité et gaz) pour le marché belge, développé par **ACT Energy**.

## Accès au dashboard

**[Ouvrir le Hedge Report](https://invictus2701.github.io/act-energy-hedge-report/statistics-preview.html)**

Le dashboard est hébergé sur GitHub Pages et mis à jour automatiquement chaque jour ouvrable à 20h00 (heure de Bruxelles).

## Données affichées

Le tableau présente les prix de settlement pour les contrats futures :

- **Belgian Power Base** (ICE Endex) — M+1, M+2, M+3, Q+1, Q+2, Q+3, Q+4, CAL+1, CAL+2, CAL+3, CAL+4
- **TTF Natural Gas Forward** (ICE Endex) — M+1, M+2, M+3, Q+1, Q+2, Q+3, Q+4, CAL+1, CAL+2, CAL+3, CAL+4, S+1, S+2, S+3

Pour chaque contrat, le dashboard affiche les 6 dernières dates de cotation ainsi que la variation journalière (VarD1).

## Architecture

```
scrape_elexys.py          Scraper des pages publiques Elexys (Power + Gas)
hedge_core.py             Moteur de calcul : upsert, rolling codes, génération cockpit
load_history_xls.py       Import initial depuis fichiers XLS historiques
statistics-preview.html   Dashboard HTML (vanilla JS, pas de framework)
market_history.json       Base de données des prix (JSON, ~68 contrats, depuis 2004)
statistics-data.json      Données cockpit pour le dashboard (HTTP)
statistics-data.js        Données cockpit en JS (compatible file://)
```

## Pipeline automatisée

Un workflow GitHub Actions (`daily_update.yml`) tourne du lundi au vendredi :

1. **Scrape** — Récupère les derniers prix sur les pages publiques Elexys
2. **Upsert** — Met à jour `market_history.json` (idempotent, pas de doublons)
3. **Cockpit** — Régénère `statistics-data.json` et `.js` avec les 6 dernières dates
4. **Commit** — Pousse les fichiers mis à jour sur `main`
5. **Deploy** — GitHub Pages se redéploie automatiquement

Le workflow peut aussi être déclenché manuellement via le bouton "Run workflow" dans l'onglet Actions.

## Sources de données

Les prix sont scrapés depuis les pages publiques d'Elexys :

- [ICE Endex Belgian Power Base](https://www.elexys.be/en/insights/ice-endex-belgian-power-base)
- [ICE Endex Dutch Natural Gas Forward](https://www.elexys.be/en/insights/ice-endex-dutch-natural-gas-forward)

## Installation locale

```bash
pip install -r requirements.txt

# Lancer le scraper manuellement
python scrape_elexys.py

# Mode dry-run (affiche sans écrire)
python scrape_elexys.py --dry-run
```

## Palette de couleurs

| Couleur | Hex | Usage |
|---------|-----|-------|
| Bleu foncé | `#262E4B` | Fond, titres |
| Vert sauge | `#86B9B7` | Accents, bordures |
| Or | `#D3A021` | Highlights, alertes |
| Vert pomme | `#A4D65E` | Indicateurs positifs |

---

*Développé par [ACT Energy](https://www.act-energy.be) — Conseil indépendant en gestion énergétique B2B*
