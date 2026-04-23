import { useState } from "react";
import Cockpit from "./Cockpit";
import Spot from "./Spot";
import { downloadPdf } from "./utils/exportPdf";

const C = { navy: "#262E4B", gold: "#D3A021" };

function ActEnergyLogo() {
  return <img src={`${import.meta.env.BASE_URL}logo-actenergy.png`} alt="ACT Energy" className="h-10" />;
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="px-6 py-3 text-sm font-semibold tracking-wider uppercase transition-colors relative"
      style={{
        color: active ? C.navy : `${C.navy}88`,
        borderBottom: active ? `3px solid ${C.gold}` : "3px solid transparent",
      }}
    >
      {children}
    </button>
  );
}

function HedgeCoverageTab() {
  return (
    <div className="text-center py-20" style={{ color: `${C.navy}88` }}>
      <h2 className="text-xl font-semibold mb-2">Rapport de couverture</h2>
      <p className="text-sm">Cette section sera implémentée prochainement.</p>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("future");

  const today = new Date().toLocaleDateString("fr-FR", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="min-h-screen bg-white">
      {/* Top header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-gray-100">
        <ActEnergyLogo />
        <div className="flex items-center gap-4">
          <span className="text-sm capitalize" style={{ color: `${C.navy}99` }}>{today}</span>
          <button
            onClick={() => downloadPdf(tab)}
            className="px-5 py-2 border-2 rounded-md text-sm font-semibold transition-colors"
            style={{ borderColor: C.navy, color: C.navy }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = C.navy;
              e.currentTarget.style.color = "#FFFFFF";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = C.navy;
            }}
          >
            Télécharger PDF
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="flex px-8 border-b border-gray-100 bg-white sticky top-0 z-10">
        <TabButton active={tab === "future"} onClick={() => setTab("future")}>
          Future
        </TabButton>
        <TabButton active={tab === "spot"} onClick={() => setTab("spot")}>
          Spot
        </TabButton>
        <TabButton active={tab === "coverage"} onClick={() => setTab("coverage")}>
          Rapport de couverture
        </TabButton>
      </nav>

      {/* Main */}
      <main id="cockpit-printable" className="max-w-[1400px] mx-auto px-8 py-8">
        {tab === "future"   && <Cockpit />}
        {tab === "spot"     && <Spot />}
        {tab === "coverage" && <HedgeCoverageTab />}
      </main>
    </div>
  );
}
