/**
 * Export PDF / impression via le dialogue natif du navigateur.
 *
 * Pourquoi ce choix :
 *  - L'utilisateur a acces a tous les reglages (format, orientation, marges,
 *    echelle, imprimante, "enregistrer au format PDF", apercu...).
 *  - Le rendu est pixel-perfect (pas de capture canvas qui peut flouter).
 *  - Les regles @media print dans index.css :
 *      - masquent l'UI (tabs, boutons, header)
 *      - revelent les details masques en mode normal (Min/Max/Moy, bande
 *        de deltas du Slope Chart)
 *      - forcent un saut de page entre chaque .pdf-section
 *      - preservent les couleurs de fond (print-color-adjust: exact)
 *
 * Le nom de fichier propose par defaut vient de document.title.
 * On le positionne dynamiquement selon l'onglet actif puis on restaure
 * le titre d'origine une fois le dialogue ferme (afterprint).
 */

const TAB_FILE_SUFFIX = {
  future:   "Future",
  spot:     "Spot",
  coverage: "Hedge-Report",
};

export function downloadPdf(tab = "future") {
  const today  = new Date().toISOString().slice(0, 10);
  const suffix = TAB_FILE_SUFFIX[tab] || "Future";

  const previousTitle = document.title;
  document.title = `Act-Energy-${suffix}-${today}`;

  const restore = () => {
    document.title = previousTitle;
    window.removeEventListener("afterprint", restore);
  };
  window.addEventListener("afterprint", restore);

  // Declenche le dialogue d'impression natif. L'utilisateur voit l'apercu
  // et choisit "Enregistrer au format PDF" ou une imprimante physique.
  window.print();
}
