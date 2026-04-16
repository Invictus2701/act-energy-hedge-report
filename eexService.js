/**
 * Market Data Service (Hedge Report)
 * --------------------------------------------------------------
 * Charge les Settlement Prices pour les futures Belgian Power Base
 * et TTF Natural Gas (M+1, Q+1, Q+2, Y+1, Y+2, Y+3).
 *
 * Source : statistics-data.json — fichier régénéré quotidiennement
 * par la pipeline Python :
 *   • load_history_xls.py  → reconstruit l'historique depuis les .xls
 *                            (powerbefwd_*, GasTTF_*) du dossier /data
 *   • scrape_elexys.py     → ajoute le settlement du jour publié par
 *                            Elexys (https://my.elexys.be)
 *
 * Plus de fallback mock, plus d'appel EEX commercial. Les données
 * sont déjà calculées côté Python (varD1, varW1, avg/max/min YTD).
 */

// Permet d'override le chemin via env (ex. CDN, route API)
const STATS_URL =
  (typeof process !== "undefined" &&
    process.env &&
    process.env.REACT_APP_STATS_URL) ||
  "/statistics-data.json";

/** Retourne les N derniers jours ouvrés (lun-ven) avant `fromDate` (incluse). */
export function getLastBusinessDays(n = 6, fromDate = new Date()) {
  const days = [];
  const d = new Date(fromDate);
  while (days.length < n) {
    const wd = d.getDay();
    if (wd !== 0 && wd !== 6) days.unshift(new Date(d));
    d.setDate(d.getDate() - 1);
  }
  return days;
}

/**
 * Point d'entrée principal : renvoie la structure JSON attendue par le
 * composant StatisticsTable. Charge simplement le fichier généré par la
 * pipeline Python.
 */
export async function fetchStatistics({ url = STATS_URL } = {}) {
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) {
    throw new Error(
      `Impossible de charger ${url} (HTTP ${res.status}). ` +
        `Vérifier que la pipeline Python a bien généré statistics-data.json.`
    );
  }
  return res.json();
}
