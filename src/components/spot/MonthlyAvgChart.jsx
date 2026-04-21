import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

const C = { navy: "#262E4B", teal: "#86B9B7", gold: "#D3A021", green: "#A4D65E" };
const YEAR_COLORS = [C.navy, C.teal, C.gold];
const MONTHS_FR = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin",
                   "Juil", "Août", "Sept", "Oct", "Nov", "Déc"];

export default function MonthlyAvgChart({ title, source, data }) {
  if (!data || !data.years?.length) return null;

  // Build rows: one row per month, one column per year
  const rows = MONTHS_FR.map((m, i) => {
    const row = { month: m };
    data.years.forEach((y) => {
      row[y.year] = y.values[i];
    });
    return row;
  });

  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: `${C.navy}12` }}>
      <h3 className="text-center text-sm font-bold tracking-wider uppercase mb-3" style={{ color: C.navy }}>
        {title}
      </h3>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#9CA3AF" }} />
          <YAxis
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            width={50}
            label={{ value: "EUR/MWh", angle: -90, position: "insideLeft",
                     style: { fontSize: 10, fill: "#9CA3AF" } }}
          />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }}
                   formatter={(v) => v == null ? "—" : Number(v).toFixed(2)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {data.years.map((y, i) => (
            <Bar
              key={y.year}
              dataKey={String(y.year)}
              fill={YEAR_COLORS[i % YEAR_COLORS.length]}
              radius={[3, 3, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      <p className="text-[10px] text-right mt-1" style={{ color: "#9CA3AF" }}>
        Source : {source}
      </p>
    </div>
  );
}
