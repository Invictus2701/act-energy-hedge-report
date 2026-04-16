import { useEffect, useState } from "react";
import StatisticsTable from "./components/StatisticsTable";
import ChartsGrid from "./components/ChartsGrid";
import { downloadPdf } from "./utils/exportPdf";
import { downloadExcel } from "./utils/exportExcel";

function ActEnergyLogo() {
  return (
    <img src="/logo-actenergy.png" alt="ACT Energy" className="h-10" />
  );
}

export default function Cockpit() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/data/statistics-data.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="p-8 text-red-600">Erreur : {error}</div>;
  if (!data) return <div className="p-8 text-navy">Chargement...</div>;

  const today = new Date().toLocaleDateString("fr-FR", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-gray-100">
        <ActEnergyLogo />
        <div className="flex items-center gap-4">
          <span className="text-sm text-navy/60 capitalize">{today}</span>
          <button
            onClick={downloadPdf}
            className="px-5 py-2 border-2 border-navy rounded-md text-navy text-sm font-semibold hover:bg-navy hover:text-white transition-colors"
          >
            Download PDF
          </button>
        </div>
      </header>

      {/* Main */}
      <main id="cockpit-printable" className="max-w-[1400px] mx-auto px-8 py-8">
        <StatisticsTable data={data} onDownloadExcel={() => downloadExcel(data)} />
        <ChartsGrid />
      </main>
    </div>
  );
}
