import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

const C = { navy: "#262E4B", green: "#A4D65E" };

export default function BelpexHourlyChart({ data }) {
  if (!data || !data.weeks?.length) return null;

  // Merge the 2 weeks into one row-per-hour dataset for Recharts
  const rows = data.xLabels.map((lbl, i) => {
    const row = { x: lbl };
    data.weeks.forEach((w) => {
      row[w.label] = w.values[i];
    });
    return row;
  });

  const colors = [C.navy, C.green];

  // Only show the day labels at hour 00 (every 24th tick)
  const ticks = data.xLabels.filter((_, i) => i % 24 === 0);
  const tickFmt = (v) => v.split(" ")[0];

  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: `${C.navy}12` }}>
      <h3 className="text-center text-sm font-bold tracking-wider uppercase mb-3" style={{ color: C.navy }}>
        Belpex horaire &mdash; comparaison semaines
      </h3>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="x"
            ticks={ticks}
            tickFormatter={tickFmt}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            width={50}
            label={{ value: "EUR/MWh", angle: -90, position: "insideLeft",
                     style: { fontSize: 10, fill: "#9CA3AF" } }}
          />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }}
                   formatter={(v) => v == null ? "—" : Number(v).toFixed(2)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {data.weeks.map((w, i) => (
            <Line
              key={w.label}
              dataKey={w.label}
              stroke={colors[i % colors.length]}
              strokeWidth={1.8}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      <p className="text-[10px] text-right mt-1" style={{ color: "#9CA3AF" }}>
        Source : EPEX Spot Belgium (Belpex)
      </p>
    </div>
  );
}
