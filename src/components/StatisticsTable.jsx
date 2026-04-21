import React from "react";

/* ───── Palette ACT Energy ───── */
const C = {
  navy: "#262E4B",
  teal: "#86B9B7",
  gold: "#D3A021",
  green: "#A4D65E",
  redVar: "#C0392B",
  greenVar: "#A4D65E",
  rowOdd: "#FFFFFF",
  rowEven: "#F9FAFB",
};

/* ───── Icones SVG ───── */
const BoltIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
       stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const FlameIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none"
       stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
  </svg>
);

const ChartIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
       stroke={C.teal} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="12" width="4" height="9" />
    <rect x="10" y="6" width="4" height="15" />
    <rect x="17" y="9" width="4" height="12" />
  </svg>
);

/* ───── Formatters ───── */
const fmt = (v) =>
  v == null || isNaN(v)
    ? "\u2014"
    : Number(v).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

const fmtPct = (v) =>
  v == null || isNaN(v)
    ? "\u2014"
    : `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}%`;

/* ───── Variation cell color ───── */
function varStyle(v) {
  if (v == null || isNaN(v)) return {};
  // Negatif = vert, positif ou zero = orange (gold)
  return v < 0
    ? { backgroundColor: C.green, color: C.navy }
    : { backgroundColor: C.gold, color: C.navy };
}

/* ───── Sub-components ───── */
function GroupHeader({ label, icon, colSpan }) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        style={{ backgroundColor: C.navy }}
        className="px-5 py-2.5 text-white text-sm font-semibold tracking-widest uppercase"
      >
        <span className="inline-flex items-center gap-2">
          {icon}
          {label}
        </span>
      </td>
    </tr>
  );
}

function ProductRow({ product, sessions, isEven }) {
  return (
    <tr style={{ backgroundColor: isEven ? C.rowEven : C.rowOdd }}>
      {/* Label */}
      <td className="px-5 py-3 font-medium whitespace-nowrap" style={{ color: C.navy }}>
        {product.label}{" "}
        <span className="text-xs opacity-50">(EUR/MWh)</span>
      </td>

      {/* 6 session prices */}
      {product.prices.map((p, i) => (
        <td key={i} className="px-3 py-3 text-center tabular-nums" style={{ color: C.navy }}>
          {fmt(p)}
        </td>
      ))}

      {/* Var D-1 */}
      <td
        className="px-3 py-3 text-center font-semibold text-sm tabular-nums"
        style={varStyle(product.varD1)}
      >
        {fmtPct(product.varD1)}
      </td>

      {/* Var W-1 */}
      <td
        className="px-3 py-3 text-center font-semibold text-sm tabular-nums"
        style={varStyle(product.varW1)}
      >
        {fmtPct(product.varW1)}
      </td>

      {/* Avg / Max / Min */}
      <td className="px-3 py-3 text-center tabular-nums" style={{ color: C.navy }}>{fmt(product.avg)}</td>
      <td className="px-3 py-3 text-center tabular-nums" style={{ color: C.navy }}>{fmt(product.max)}</td>
      <td className="px-3 py-3 text-center tabular-nums" style={{ color: C.navy }}>{fmt(product.min)}</td>
    </tr>
  );
}

/* ───── Main component ───── */
export default function StatisticsTable({ data, onDownloadExcel }) {
  const { sessions } = data.meta;
  const totalCols = 1 + sessions.length + 5; // label + dates + var×2 + avg/max/min

  return (
    <section>
      {/* Title row */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <ChartIcon />
          <h2
            className="text-2xl font-bold tracking-wider uppercase"
            style={{ color: C.navy }}
          >
            Statistiques
          </h2>
        </div>
        <p className="text-xs italic" style={{ color: C.navy, opacity: 0.6 }}>
          * MAX, MIN, MOY. &mdash; Depuis le début de l'année
        </p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border" style={{ borderColor: `${C.navy}15` }}>
        <table className="w-full text-sm border-collapse">
          <thead>
            {/* Column headers */}
            <tr style={{ backgroundColor: C.navy, color: "#FFFFFF" }}>
              <th className="px-5 py-3 text-left font-semibold">Marchés</th>
              {sessions.map((s) => (
                <th key={s.date} className="px-3 py-3 text-center font-medium">
                  <div className="text-[11px] opacity-70">{s.label}</div>
                  <div className="text-xs">{s.weekday}</div>
                </th>
              ))}
              <th className="px-3 py-3 text-center font-semibold">
                Var J-1
              </th>
              <th className="px-3 py-3 text-center font-semibold">
                Var S-1
              </th>
              <th className="px-3 py-3 text-center font-semibold">Moy.</th>
              <th className="px-3 py-3 text-center font-semibold">Max</th>
              <th className="px-3 py-3 text-center font-semibold">Min</th>
            </tr>
          </thead>

          <tbody>
            {data.markets.map((grp) => (
              <React.Fragment key={grp.group}>
                <GroupHeader
                  label={grp.group === "ELECTRICITY" ? "ÉLECTRICITÉ" : grp.group === "GAS" ? "GAZ" : grp.group}
                  icon={grp.group === "ELECTRICITY" ? <BoltIcon /> : <FlameIcon />}
                  colSpan={totalCols}
                />
                {grp.products.map((p, i) => (
                  <ProductRow
                    key={p.code}
                    product={p}
                    sessions={sessions}
                    isEven={i % 2 === 0}
                  />
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer button */}
      <div className="flex justify-center mt-6">
        <button
          onClick={onDownloadExcel}
          className="px-8 py-3 rounded-md text-sm font-bold tracking-wider uppercase transition-colors"
          style={{
            backgroundColor: "#FFFFFF",
            color: C.navy,
            border: `2px solid ${C.navy}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = C.navy;
            e.currentTarget.style.color = "#FFFFFF";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#FFFFFF";
            e.currentTarget.style.color = C.navy;
          }}
        >
          Télécharger Excel
        </button>
      </div>

      {/* Last update */}
      <p className="text-right text-xs mt-3 italic" style={{ color: C.navy, opacity: 0.45 }}>
        Dernière mise à jour : {data.meta.generatedAt?.slice(0, 10) || "N/A"}
      </p>
    </section>
  );
}
