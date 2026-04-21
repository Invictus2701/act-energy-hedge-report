import html2canvas from "html2canvas-pro";
import { jsPDF } from "jspdf";

/**
 * Capture la zone #cockpit-printable en image haute resolution
 * puis l'insere dans un PDF A4 paysage.
 */
export async function downloadPdf() {
  const el = document.getElementById("cockpit-printable");
  if (!el) return;

  // Capture haute resolution (2x) pour nettete
  const canvas = await html2canvas(el, {
    scale: 2,
    useCORS: true,
    backgroundColor: "#FFFFFF",
  });

  const imgData = canvas.toDataURL("image/png");
  const imgW = canvas.width;
  const imgH = canvas.height;

  // PDF A4 paysage
  const pdf = new jsPDF({
    orientation: "landscape",
    unit: "mm",
    format: "a4",
  });

  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const margin = 10;
  const availW = pageW - margin * 2;
  const availH = pageH - margin * 2;

  // Scale l'image pour tenir dans la page
  const ratio = Math.min(availW / imgW, availH / imgH);
  const finalW = imgW * ratio;
  const finalH = imgH * ratio;

  // Centre horizontalement
  const x = margin + (availW - finalW) / 2;
  const y = margin;

  pdf.addImage(imgData, "PNG", x, y, finalW, finalH);

  const today = new Date().toISOString().slice(0, 10);
  pdf.save(`Cockpit_ACT_Energy_${today}.pdf`);
}
