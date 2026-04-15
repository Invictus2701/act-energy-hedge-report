/**
 * EEX Market Data Service
 * --------------------------------------------------------------
 * Récupère les Settlement Prices pour les futures Belgian Power Base
 * et TTF Natural Gas (M+1, Q+1, Q+2, Y+1, Y+2, Y+3).
 *
 * IMPORTANT : L'API Market Data d'EEX (https://webservice-eex.gvsi.com)
 * requiert une souscription commerciale ("EEX Market Data Services").
 * L'authentification se fait via HTTP Basic Auth ou OAuth2 selon le
 * contrat. En dev, un fallback mock est utilisé.
 *
 * Docs officielles : https://www.eex.com/en/market-data
 * Endpoint typique  : /query/settlement_prices?symbol=<SYM>&ondate=<YYYY-MM-DD>
 */

const EEX_BASE_URL = process.env.REACT_APP_EEX_BASE_URL
  || "https://webservice-eex.gvsi.com/query";

// Mapping interne -> symboles EEX
const SYMBOLS = {
  ELECTRICITY: {
    M1: "/E.FEBYM",  // Belgian Power Base Month
    Q1: "/E.FEBYQ",  // Belgian Power Base Quarter
    Q2: "/E.FEBYQ",
    Y1: "/E.FEBYY",  // Belgian Power Base Year (calendar)
    Y2: "/E.FEBYY",
    Y3: "/E.FEBYY",
  },
  GAS: {
    M1: "/E.FGTHM",  // TTF Natural Gas Month
    Q1: "/E.FGTHQ",
    Q2: "/E.FGTHQ",
    Y1: "/E.FGTHY",
    Y2: "/E.FGTHY",
    Y3: "/E.FGTHY",
  },
};

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

/** Appel API EEX brut (1 symbole, 1 date). */
async function fetchEexSettlement(symbol, maturityOffset, date, apiKey) {
  const url = `${EEX_BASE_URL}/settlement_prices`
    + `?symbol=${encodeURIComponent(symbol)}`
    + `&maturity=${maturityOffset}`
    + `&ondate=${date.toISOString().slice(0, 10)}`;

  const res = await fetch(url, {
    headers: {
      "Authorization": `Basic ${apiKey}`,
      "Accept": "application/json",
    },
  });
  if (!res.ok) throw new Error(`EEX ${res.status} on ${symbol}@${date}`);
  const body = await res.json();
  return body?.results?.items?.[0]?.close; // settlement
}

/** Calcule Var D-1, Var W-1, Avg/Max/Min YTD. */
function buildStats(prices, ytdSeries) {
  const last = prices[prices.length - 1];
  const prev = prices[prices.length - 2];
  const weekAgo = prices[0]; // 6 sessions ago ≈ même jour W-1
  const varD1 = prev ? ((last - prev) / prev) * 100 : null;
  const varW1 = weekAgo ? ((last - weekAgo) / weekAgo) * 100 : null;

  const avg = ytdSeries.reduce((a, b) => a + b, 0) / ytdSeries.length;
  const max = Math.max(...ytdSeries);
  const min = Math.min(...ytdSeries);
  return {
    varD1: +varD1.toFixed(2),
    varW1: +varW1.toFixed(2),
    avg: +avg.toFixed(2),
    max: +max.toFixed(2),
    min: +min.toFixed(2),
  };
}

/** Point d'entrée principal : renvoie la structure JSON attendue par le composant. */
export async function fetchStatistics({ apiKey, useMock = !apiKey } = {}) {
  if (useMock) {
    const mock = await fetch("/statistics-data.json").then(r => r.json());
    return mock;
  }

  const sessions = getLastBusinessDays(6);
  const maturities = ["M1", "Q1", "Q2", "Y1", "Y2", "Y3"];
  const offsets = { M1: 1, Q1: 1, Q2: 2, Y1: 1, Y2: 2, Y3: 3 };

  async function buildGroup(group) {
    const products = [];
    for (const m of maturities) {
      const sym = SYMBOLS[group][m];
      const prices = await Promise.all(
        sessions.map(d => fetchEexSettlement(sym, offsets[m], d, apiKey))
      );
      // Série YTD : 1er janvier -> aujourd'hui (range API EEX)
      const ytdRes = await fetch(`${EEX_BASE_URL}/settlement_prices`
        + `?symbol=${encodeURIComponent(sym)}`
        + `&maturity=${offsets[m]}`
        + `&fromdate=${new Date().getFullYear()}-01-01`
        + `&todate=${sessions[sessions.length - 1].toISOString().slice(0, 10)}`,
        { headers: { Authorization: `Basic ${apiKey}` } }).then(r => r.json());
      const ytd = (ytdRes?.results?.items || []).map(i => i.close);

      products.push({
        code: `${group}_${m}`,
        label: group === "ELECTRICITY" ? `BE ${m.replace(/(\d)/, "+$1")} base`
                                       : `TTF ${m.replace(/(\d)/, "+$1")}`,
        prices: prices.map(p => +p.toFixed(2)),
        ...buildStats(prices, ytd),
      });
    }
    return { group, products };
  }

  return {
    meta: {
      module: "Statistics",
      generatedAt: new Date().toISOString(),
      source: "EEX Market Data - Settlement Prices",
      currency: "EUR", unit: "MWh",
      ytdStart: `${new Date().getFullYear()}-01-01`,
      sessions: sessions.map(d => ({
        label: `${d.getDate()}/${d.getMonth() + 1}`,
        weekday: d.toLocaleDateString("en-US", { weekday: "long" }),
        date: d.toISOString().slice(0, 10),
      })),
    },
    markets: [await buildGroup("ELECTRICITY"), await buildGroup("GAS")],
  };
}
