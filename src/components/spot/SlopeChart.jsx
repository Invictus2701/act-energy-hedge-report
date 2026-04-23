import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, LabelList,
} from "recharts";

const C = {
  navy:  "#262E4B",
  teal:  "#86B9B7",
  gold:  "#D3A021",
  green: "#A4D65E",
  mute:  "#9CA3AF",
};

// Une couleur distincte par serie. Gaz = teal (reference).
// Electricite Base = navy, Peak = or (heures de pointe), Off-peak = vert.
const SERIES_COLORS = {
  GAS_BASE:     C.teal,
  ELEC_BASE:    C.navy,
  ELEC_PEAK:    C.gold,
  ELEC_OFFPEAK: C.green,
};

const fmt    = (v) => v == null ? "—" : Number(v).toFixed(2);
const fmtPct = (v) => v == null ? "—" : `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}%`;
const fmtDelta = (v) => v == null ? "—" : `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}`;

// Abrege un label "Semaine 16 (13/04 -> 19/04)" en "S16 (13/04 → 19/04)" pour l'axe.
const shortWeek = (label) => (label || "").replace(/^Semaine\s+/, "S").replace(" ->", " →");

/** Tooltip custom : affiche Delta et Delta % pour la serie survolee. */
function SlopeTooltip({ active, payload, series }) {
  if (!active || !payload || payload.length === 0) return null;
  // payload = [{dataKey, value, color}, ...] pour la colonne survolee
  return (
    <div className="bg-white rounded-md shadow-lg border px-3 py-2 text-[11px]"
         style={{ borderColor: `${C.navy}20` }}>
      {payload.map((p) => {
        const s = series.find((x) => x.code === p.dataKey);
        if (!s) return null;
        return (
          <div key={s.code} className="flex items-center gap-2 leading-tight py-0.5">
            <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="font-semibold" style={{ color: C.navy }}>{s.label}</span>
            <span className="tabular-nums" style={{ color: C.navy }}>{fmt(p.value)} €/MWh</span>
            {s.delta != null && (
              <span
                className="tabular-nums font-semibold ml-1"
                style={{ color: s.delta < 0 ? "#0B5D1E" : "#8B0000" }}
              >
                {fmtDelta(s.delta)} ({fmtPct(s.deltaPct)})
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function SlopeChart({ data }) {
  if (!data || !data.weeks?.length || !data.series?.length) return null;

  // Chaque ligne = 1 semaine, une colonne par serie.
  const chartData = data.weeks.map((w, i) => {
    const row = { x: shortWeek(w.label) };
    for (const s of data.series) row[s.code] = s.values[i];
    return row;
  });

  // Domaine Y resserre sur les valeurs reelles (±5% de padding)
  // pour accentuer l'ampleur visuelle des variations.
  const allVals = data.series.flatMap((s) => s.values.filter((v) => v != null));
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const pad  = (maxV - minV) * 0.08 || 1;
  const yDomain = [Math.floor(minV - pad), Math.ceil(maxV + pad)];

  return (
    <div className="slope-chart bg-white rounded-lg border p-5"
         style={{ borderColor: `${C.navy}12` }}>
      <h3 className="text-center text-sm font-bold tracking-wider uppercase mb-3"
          style={{ color: C.navy }}>
        Comparaison hebdomadaire &mdash; Gaz &amp; Électricité
      </h3>

      {/* Container resserre (max 780px) pour rapprocher les 2 semaines
          horizontalement => angles de pente plus marques. */}
      <div className="max-w-[780px] mx-auto">
        <ResponsiveContainer width="100%" height={420}>
          <LineChart data={chartData} margin={{ top: 20, right: 90, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="x"
              padding={{ left: 60, right: 60 }}
              tick={{ fontSize: 12, fill: C.navy, fontWeight: 600 }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: C.mute }}
              width={50}
              label={{ value: "EUR/MWh", angle: -90, position: "insideLeft",
                       style: { fontSize: 10, fill: C.mute } }}
              domain={yDomain}
            />
            <Tooltip content={<SlopeTooltip series={data.series} />} />
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
                    formatter={(code) => {
                      const s = data.series.find((x) => x.code === code);
                      return s ? s.label : code;
                    }} />
            {data.series.map((s) => (
              <Line
                key={s.code}
                dataKey={s.code}
                stroke={SERIES_COLORS[s.code] || C.navy}
                strokeWidth={2.5}
                dot={{ r: 5, strokeWidth: 2, fill: "#FFFFFF" }}
                connectNulls
                isAnimationActive={false}
              >
                {/* Label de valeur : prix a gauche (S-1), prix + fleche Δ%
                    a droite (S courante) pour donner un signal directionnel
                    fort : ▲ rouge = hausse, ▼ vert = baisse. */}
                <LabelList
                  dataKey={s.code}
                  content={(props) => {
                    const { x, y, value, index } = props;
                    if (value == null) return null;
                    const isLast  = index === chartData.length - 1;
                    const color   = SERIES_COLORS[s.code] || C.navy;
                    if (!isLast) {
                      return (
                        <text x={x - 10} y={y + 3} textAnchor="end"
                              fill={color} fontSize={10} fontWeight={600}>
                          {fmt(value)}
                        </text>
                      );
                    }
                    const up       = s.deltaPct != null && s.deltaPct > 0;
                    const arrowCol = up ? "#8B0000" : "#0B5D1E";
                    const arrow    = up ? "▲" : "▼";
                    return (
                      <g>
                        <text x={x + 10} y={y + 3} textAnchor="start"
                              fill={color} fontSize={10} fontWeight={600}>
                          {fmt(value)}
                        </text>
                        <text x={x + 48} y={y + 3} textAnchor="start"
                              fill={arrowCol} fontSize={11} fontWeight={700}>
                          {arrow} {fmtPct(s.deltaPct)}
                        </text>
                      </g>
                    );
                  }}
                />
              </Line>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Bande de deltas : masquee par defaut, visible au survol ET en PDF.
          CSS regles dans index.css (.slope-deltas). */}
      <div className="slope-deltas flex-wrap gap-2 mt-3 pt-3"
           style={{ borderTop: `1px solid ${C.navy}10` }}>
        {data.series.map((s) => (
          <div
            key={s.code}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px]"
            style={{ backgroundColor: "#FAFAF7", border: `1px solid ${C.navy}10` }}
          >
            <span className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: SERIES_COLORS[s.code] }} />
            <span className="font-semibold" style={{ color: C.navy }}>{s.label}</span>
            <span className="tabular-nums" style={{ color: C.mute }}>
              {fmt(s.values[0])} → {fmt(s.values[1])}
            </span>
            <span
              className="tabular-nums font-semibold"
              style={{ color: s.delta == null ? C.mute : s.delta < 0 ? "#0B5D1E" : "#8B0000" }}
            >
              {fmtDelta(s.delta)} ({fmtPct(s.deltaPct)})
            </span>
          </div>
        ))}
      </div>

      <p className="text-[10px] text-right mt-2" style={{ color: C.mute }}>
        Source : EPEX Spot Belgium (Belpex) &amp; ICIS Heren Gas TTF DAH
      </p>
    </div>
  );
}
