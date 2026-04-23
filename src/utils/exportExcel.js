import * as XLSX from "xlsx";

/**
 * Genere et telecharge un fichier Excel a partir des donnees statistics-data.json.
 * Ordre des colonnes identique au tableau Statistiques du Cockpit :
 *   Marches | 6 sessions | Moy. | Min | Max | Var J-1 | Var S-1
 */
export function downloadExcel(data) {
  const { sessions } = data.meta;
  const wb = XLSX.utils.book_new();

  const header = [
    "Marchés",
    ...sessions.map((s) => `${s.label} ${s.weekday}`),
    "Moy.",
    "Min",
    "Max",
    "Var J-1",
    "Var S-1",
  ];

  const rows = [header];

  for (const grp of data.markets) {
    rows.push([grp.group]);

    for (const p of grp.products) {
      rows.push([
        `${p.label} (EUR/MWh)`,
        ...p.prices.map((v) => (v != null ? v : "")),
        p.avg ?? "",
        p.min ?? "",
        p.max ?? "",
        p.varD1 != null ? p.varD1 / 100 : "",
        p.varW1 != null ? p.varW1 / 100 : "",
      ]);
    }
  }

  const ws = XLSX.utils.aoa_to_sheet(rows);

  ws["!cols"] = [
    { wch: 26 },
    ...sessions.map(() => ({ wch: 14 })),
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
    { wch: 10 },
  ];

  // Formater les 2 dernieres colonnes (Var J-1, Var S-1) en pourcentage
  const varD1Col = 1 + sessions.length + 3;   // apres Moy/Min/Max
  const varW1Col = varD1Col + 1;
  for (let r = 1; r < rows.length; r++) {
    const addrD1 = XLSX.utils.encode_cell({ r, c: varD1Col });
    const addrW1 = XLSX.utils.encode_cell({ r, c: varW1Col });
    if (ws[addrD1] && typeof ws[addrD1].v === "number") ws[addrD1].z = "0.00%";
    if (ws[addrW1] && typeof ws[addrW1].v === "number") ws[addrW1].z = "0.00%";
  }

  XLSX.utils.book_append_sheet(wb, ws, "Statistiques");

  const lastSession = sessions[sessions.length - 1]?.date || "export";
  XLSX.writeFile(wb, `Cockpit_ACT_Energy_${lastSession}.xlsx`);
}
