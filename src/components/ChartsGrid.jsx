import React, { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

/* ───── Palette ACT Energy ───── */
const C = {
  navy: "#262E4B",
  teal: "#86B9B7",
  gold: "#D3A021",
  green: "#A4D65E",
};

/* Couleurs des courbes par rang : noir, vert, rouge (comme le prototype) */
const LINE_COLORS = [C.navy, "#2E8B57", "#C0392B"];

/* ───── Config des 6 graphiques (grille 3 lignes x 2 colonnes) ─────
   Ordre horizontal : Electricite a gauche, Gaz a droite.
   Ordre vertical   : Annuel, Trimestriel, Mensuel.                  */
const CHARTS = [
  // Ligne 1 : Annuel
  {
    title: "Électricité à terme — Annuel",
    codes: ["BE_POWER_BASE_Y1", "BE_POWER_BASE_Y2", "BE_POWER_BASE_Y3"],
    labels: ["BE A+1 base", "BE A+2 base", "BE A+3 base"],
  },
  {
    title: "Gaz à terme — Annuel",
    codes: ["TTF_NG_Y1", "TTF_NG_Y2", "TTF_NG_Y3"],
    labels: ["TTF A+1", "TTF A+2", "TTF A+3"],
  },
  // Ligne 2 : Trimestriel
  {
    title: "Électricité à terme — Trimestriel",
    codes: ["BE_POWER_BASE_Q1", "BE_POWER_BASE_Q2", "BE_POWER_BASE_Q3"],
    labels: ["BE T+1 base", "BE T+2 base", "BE T+3 base"],
  },
  {
    title: "Gaz à terme — Trimestriel",
    codes: ["TTF_NG_Q1", "TTF_NG_Q2", "TTF_NG_Q3"],
    labels: ["TTF T+1", "TTF T+2", "TTF T+3"],
  },
  // Ligne 3 : Mensuel
  {
    title: "Électricité à terme — Mensuel",
    codes: ["BE_POWER_BASE_M1", "BE_POWER_BASE_M2", "BE_POWER_BASE_M3"],
    labels: ["BE M+1 base", "BE M+2 base", "BE M+3 base"],
  },
  {
    title: "Gaz à terme — Mensuel",
    codes: ["TTF_NG_M1", "TTF_NG_M2", "TTF_NG_M3"],
    labels: ["TTF M+1", "TTF M+2", "TTF M+3"],
  },
];

/* ───── Helpers ───── */
const fmt = (v) =>
  v == null ? "\u2014" : Number(v).toFixed(2);

const fmtAxis = (v) =>
  v == null ? "" : Number(v).toFixed(0);

const fmtDate = (iso) => {
  if (!iso) return "";
  const [, m] = iso.split("-");
  const mois = ["", "Janv", "Févr", "Mars", "Avr", "Mai", "Juin",
                "Juil", "Août", "Sept", "Oct", "Nov", "Déc"];
  return `${mois[parseInt(m)]} '${iso.slice(2, 4)}`;
};

/* ───── Prepare chart data ───── */
function buildChartData(history, codes) {
  // Collect all dates across the codes
  const dateSet = new Set();
  for (const code of codes) {
    const series = history[code] || {};
    Object.keys(series).forEach((d) => dateSet.add(d));
  }
  const dates = [...dateSet].sort();

  return dates.map((d) => {
    const row = { date: d };
    for (const code of codes) {
      row[code] = history[code]?.[d] ?? null;
    }
    return row;
  });
}

/* ───── Single chart + mini table ───── */
function ChartPanel({ title, codes, labels, history }) {
  const data = buildChartData(history, codes);
  const lastRow = data.length > 0 ? data[data.length - 1] : {};

  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: `${C.navy}12` }}>
      <h3
        className="text-center text-sm font-bold tracking-wider uppercase mb-3"
        style={{ color: C.navy }}
      >
        {title}
      </h3>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDate}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis
            tickFormatter={fmtAxis}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            width={45}
            domain={["auto", "auto"]}
          />
          <Tooltip
            labelFormatter={(d) => d}
            formatter={(val, name) => {
              const idx = codes.indexOf(name);
              return [fmt(val), labels[idx] || name];
            }}
            contentStyle={{ fontSize: 12, borderRadius: 6 }}
          />
          {codes.map((code, i) => (
            <Line
              key={code}
              dataKey={code}
              stroke={LINE_COLORS[i]}
              strokeWidth={1.5}
              dot={false}
              connectNulls
              name={code}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex justify-center gap-4 mt-2 mb-3">
        {labels.map((lbl, i) => (
          <div key={lbl} className="flex items-center gap-1.5">
            <div
              className="w-4 h-[2px] rounded"
              style={{ backgroundColor: LINE_COLORS[i] }}
            />
            <span className="text-[10px]" style={{ color: "#6B7280" }}>{lbl}</span>
          </div>
        ))}
      </div>

      {/* Mini table */}
      <table className="w-full text-xs border-collapse">
        <tbody>
          {codes.map((code, i) => (
            <tr
              key={code}
              className={i % 2 === 0 ? "bg-gray-50" : "bg-white"}
            >
              <td className="px-3 py-1.5 font-medium" style={{ color: C.navy }}>
                {labels[i]}
              </td>
              <td
                className="px-3 py-1.5 text-right font-semibold tabular-nums"
                style={{ color: C.navy }}
              >
                {fmt(lastRow[code])} €/MWh
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ───── Main grid ───── */
const TrendIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
       stroke={C.teal} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

export default function ChartsGrid() {
  const [history, setHistory] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/master_history.json`)
      .then((r) => r.json())
      .then(setHistory)
      .catch((e) => console.error("ChartsGrid load error:", e));
  }, []);

  if (!history) return null;

  return (
    // Une seule .pdf-section qui englobe tout : titre + grille 3x2.
    // => 1 page PDF pour l'ensemble du bloc "Prix & Tendances du Marche".
    <section className="pdf-section mt-10">
      <div className="flex items-center gap-3 mb-5">
        <TrendIcon />
        <h2
          className="text-2xl font-bold tracking-wider uppercase"
          style={{ color: C.navy }}
        >
          Prix &amp; Tendances du Marché
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {CHARTS.map((cfg) => (
          <ChartPanel
            key={cfg.title}
            title={cfg.title}
            codes={cfg.codes}
            labels={cfg.labels}
            history={history}
          />
        ))}
      </div>
    </section>
  );
}
