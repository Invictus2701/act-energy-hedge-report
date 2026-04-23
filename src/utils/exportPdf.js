import html2canvas from "html2canvas-pro";
import { jsPDF } from "jspdf";

/**
 * Export PDF section par section : chaque element portant la classe
 * .pdf-section est capture independamment et place sur sa propre page A4
 * paysage. Garantit qu'aucun graphique / tableau ne se retrouve coupe
 * entre deux pages.
 *
 * Logique :
 *   1. Ajoute body.pdf-exporting -> force l'affichage des details
 *      masques en mode normal (Min/Max/Moy des PriceCorridor).
 *   2. Recupere toutes les .pdf-section a l'interieur de #cockpit-printable.
 *   3. Pour chaque section : capture via html2canvas-pro puis insertion
 *      dans une nouvelle page PDF, mise a l'echelle pour tenir entierement
 *      sur la page (sans deformation).
 *   4. Fallback : si aucune .pdf-section n'est trouvee, on capture la zone
 *      entiere en une seule image (ancien comportement).
 */
async function _captureNode(node) {
  return html2canvas(node, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#FFFFFF",
    windowWidth: node.scrollWidth,
  });
}

function _addCenteredImage(pdf, canvas) {
  const pageW  = pdf.internal.pageSize.getWidth();
  const pageH  = pdf.internal.pageSize.getHeight();
  const margin = 8;
  const availW = pageW - margin * 2;
  const availH = pageH - margin * 2;

  // Ratio pour que la section tienne entierement dans la zone utile,
  // en preservant son aspect d'origine.
  const ratio  = Math.min(availW / canvas.width, availH / canvas.height);
  const w = canvas.width  * ratio;
  const h = canvas.height * ratio;
  const x = margin + (availW - w) / 2;
  const y = margin + (availH - h) / 2;

  pdf.addImage(canvas.toDataURL("image/png"), "PNG", x, y, w, h);
}

// Mapping du nom d'onglet actif -> suffixe de nom de fichier.
const TAB_FILE_SUFFIX = {
  future:   "Future",
  spot:     "Spot",
  coverage: "Hedge-Report",
};

export async function downloadPdf(tab = "future") {
  const root = document.getElementById("cockpit-printable");
  if (!root) return;

  document.body.classList.add("pdf-exporting");
  // 2 frames pour laisser le navigateur repeindre avec les details reveles.
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

  try {
    const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
    const sections = Array.from(root.querySelectorAll(".pdf-section"));

    if (sections.length > 0) {
      for (let i = 0; i < sections.length; i++) {
        const canvas = await _captureNode(sections[i]);
        if (i > 0) pdf.addPage();
        _addCenteredImage(pdf, canvas);
      }
    } else {
      // Fallback : pas de balisage -> une seule capture.
      const canvas = await _captureNode(root);
      _addCenteredImage(pdf, canvas);
    }

    const today  = new Date().toISOString().slice(0, 10);
    const suffix = TAB_FILE_SUFFIX[tab] || "Future";
    pdf.save(`Act-Energy-${suffix}-${today}.pdf`);
  } finally {
    document.body.classList.remove("pdf-exporting");
  }
}
