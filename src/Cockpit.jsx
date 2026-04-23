import { useEffect, useState } from "react";
import StatisticsTable from "./components/StatisticsTable";
import ChartsGrid from "./components/ChartsGrid";
import { downloadExcel } from "./utils/exportExcel";

export default function Cockpit() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/statistics-data.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-8 text-red-600">Erreur : {error}</div>;
  if (!data) return <div className="p-8" style={{ color: "#262E4B" }}>Chargement…</div>;

  return (
    <>
      <StatisticsTable data={data} onDownloadExcel={() => downloadExcel(data)} />
      <ChartsGrid />
    </>
  );
}
