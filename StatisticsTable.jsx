import React, { useEffect, useState } from "react";
import { fetchStatistics } from "./eexService";

// Palette ACT Energy
const C = {
  bgHeader: "#262E4B",   // nuit profonde - bandeau titre & groupes
  accent:   "#86B9B7",   // vert-bleu doux - icônes
  gold:     "#D3A021",   // or - accents éventuels
  green:    "#A4D65E",   // vert clair - colonnes variation
};

// Icônes SVG minimalistes (blanc)
const BoltIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
       stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);
const FlameIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
       stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
  </svg>
);

const fmt = (v) =>
  v == null || isNaN(v) ? "—" : Number(v).toLocaleString("en-US", {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });

const fmtPct = (v) =>
  v == null || isNaN(v) ? "—" : `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}%`;

function GroupHeader({ label, icon, cols }) {
  return (
    <tr>
      <td colSpan={cols}
          style={{ background: C.bgHeader, color: "white" }}
          className="px-4 py-2 font-semibold tracking-wide uppercase text-sm">
        <span className="inline-flex items-center gap-2">
          {icon}{label}
        </span>
      </td>
    </tr>
  );
}

function ProductRow({ product, sessions, zebra }) {
  return (
    <tr className={zebra ? "bg-[#faf7f0]" : "bg-[#f5f1e6]"}>
      <td className="px-4 py-2 text-[#262E4B] font-medium">
        {product.label} <span className="text-xs opacity-60">(EUR/MWh)</span>
      </td>
      {product.prices.map((p, i) => (
        <td key={i} className="px-3 py-2 text-center text-[#262E4B]">{fmt(p)}</td>
      ))}
      <td className="px-3 py-2 text-center font-semibold"
          style={{ background: C.green, color: "white" }}>
        {fmtPct(product.varD1)}
      </td>
      <td className="px-3 py-2 text-center font-semibold"
          style={{ background: C.green, color: "white" }}>
        {fmtPct(product.varW1)}
      </td>
      <td className="px-3 py-2 text-center text-[#262E4B]">{fmt(product.avg)}</td>
      <td className="px-3 py-2 text-center text-[#262E4B]">{fmt(product.max)}</td>
      <td className="px-3 py-2 text-center text-[#262E4B]">{fmt(product.min)}</td>
    </tr>
  );
}

export default function StatisticsTable({ url }) {
  const [data, setData] = useState(null);
  const [err, setErr]   = useState(null);

  useEffect(() => {
    fetchStatistics({ url }).then(setData).catch(e => setErr(e.message));
  }, [url]);

  if (err)  return <div className="p-6 text-red-600">Erreur : {err}</div>;
  if (!data) return <div className="p-6 text-[#262E4B]">Chargement…</div>;

  const sessions = data.meta.sessions;
  const cols = 1 + sessions.length + 5; // label + 6 dates + 2 var + avg/max/min

  return (
    <div className="w-full bg-[#faf7f0] p-6 rounded-lg">
      {/* Titre */}
      <div className="flex items-center justify-center gap-3 mb-4">
        <span style={{ color: C.accent }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2">
            <rect x="3"  y="12" width="4" height="9"/>
            <rect x="10" y="6"  width="4" height="15"/>
            <rect x="17" y="9"  width="4" height="12"/>
          </svg>
        </span>
        <h2 className="text-xl font-semibold tracking-wider text-[#262E4B]">
          STATISTICS
        </h2>
      </div>

      <div className="overflow-x-auto rounded-md border border-[#262E4B]/10">
        <table className="w-full text-sm border-collapse">
          {/* En-tête colonnes */}
          <thead>
            <tr style={{ background: C.bgHeader, color: "white" }}>
              <th className="px-4 py-3 text-left font-semibold">Markets</th>
              {sessions.map((s) => (
                <th key={s.date} className="px-3 py-2 text-center font-medium">
                  <div className="text-xs opacity-80">{s.label}</div>
                  <div>{s.weekday}</div>
                </th>
              ))}
              <th className="px-3 py-2 text-center" style={{ background: C.green, color: "white" }}>Var D-1</th>
              <th className="px-3 py-2 text-center" style={{ background: C.green, color: "white" }}>Var W-1</th>
              <th className="px-3 py-2 text-center font-medium">Avg.</th>
              <th className="px-3 py-2 text-center font-medium">Max</th>
              <th className="px-3 py-2 text-center font-medium">Min</th>
            </tr>
            <tr>
              <td colSpan={cols} className="text-right pr-4 text-xs italic py-1 text-[#262E4B]/70">
                * MAX, MIN, AVG - Since the beginning of the year
              </td>
            </tr>
          </thead>

          <tbody>
            {data.markets.map((grp) => (
              <React.Fragment key={grp.group}>
                <GroupHeader
                  label={grp.group}
                  icon={grp.group === "ELECTRICITY" ? <BoltIcon/> : <FlameIcon/>}
                  cols={cols}
                />
                {grp.products.map((p, i) => (
                  <ProductRow key={p.code} product={p} sessions={sessions} zebra={i % 2 === 1}/>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
