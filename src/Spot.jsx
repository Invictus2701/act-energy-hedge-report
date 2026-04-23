import { useEffect, useState } from "react";
import BelpexHourlyChart from "./components/spot/BelpexHourlyChart";
import TtfDahDailyChart from "./components/spot/TtfDahDailyChart";
import MonthlyAvgChart from "./components/spot/MonthlyAvgChart";

const C = { navy: "#262E4B", teal: "#86B9B7" };

const TrendIcon = () => (
  <svg width="26" height="26" viewBox="0 0 24 24" fill="none"
       stroke={C.teal} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
  </svg>
);

export default function Spot() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/spot-data.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-8 text-red-600">Erreur : {error}</div>;
  if (!data) return <div className="p-8" style={{ color: C.navy }}>Chargement…</div>;

  return (
    <section>
      <div className="flex items-center gap-3 mb-6">
        <TrendIcon />
        <h2 className="text-2xl font-bold tracking-wider uppercase" style={{ color: C.navy }}>
          Marché Spot
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <BelpexHourlyChart data={data.belpexHourly} />
        <TtfDahDailyChart  data={data.ttfDahDaily} />
        <MonthlyAvgChart
          title="Belpex — Moyennes mensuelles par année"
          source="EPEX Spot Belgium (Belpex)"
          data={data.belpexMonthly}
        />
        <MonthlyAvgChart
          title="TTF DAH — Moyennes mensuelles par année"
          source="ICIS Heren Gas TTF DAH"
          data={data.ttfDahMonthly}
        />
      </div>

      <p className="text-right text-xs mt-4 italic" style={{ color: C.navy, opacity: 0.45 }}>
        Données : {data.meta.sourceDir} — Dernière mise à jour : {data.meta.generatedAt?.slice(0, 10)}
      </p>
    </section>
  );
}
