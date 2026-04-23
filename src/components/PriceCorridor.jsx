/**
 * PriceCorridor — Bullet chart compact + deltas contextualises par sigma.
 *
 *   [43,37]                  ← prix actuel
 *      ●
 *   ┄┄┄┄│┄┄┄┄┄┄┄┄┄┄┄┄┄┄       ← track [min, max] + moy.
 *   Min 27.40      Max 61.85
 *          Moy. 41.01
 *
 *   [Δ J-1 +3.87%]  [Δ S-1 +5.20%]
 *
 * Deltas J-1 / S-1 :
 *  - Couleur = signe (negatif=vert, positif=or)
 *  - Intensite = |z-score| clampe sur [0,1] avec z = var / sigma_journalier
 *    Plus l'anomalie est forte relativement a la volatilite historique
 *    du produit, plus la cellule est saturee. Un +4% sur un produit
 *    tres volatile (sigma=6%) apparait pale, le meme +4% sur un produit
 *    calme (sigma=1%) apparait intense. C'est la lecture "anomalie marche".
 */

const C = {
  navy:  "#262E4B",
  gold:  "#D3A021",
  green: "#A4D65E",
  track: "#E5E7EB",
  mute:  "#9CA3AF",
};

const fmt = (v) =>
  v == null || isNaN(v)
    ? "\u2014"
    : Number(v).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

const fmtPct = (v) =>
  v == null || isNaN(v)
    ? "\u2014"
    : `${v > 0 ? "+" : ""}${Number(v).toFixed(2)}%`;

// Echelle divergente symetrique centree sur 0 % :
//  -10 % : vert sapin (#0B5D1E) -- baisse marquee, fort repit
//    0 % : blanc                -- point neutre
//  +10 % : rouge sang (#8B0000) -- hausse marquee, tension maximale
// Interpolation lineaire entre chaque stop, saturation aux bornes.
const STOPS = [
  { x: -10, hex: "#0B5D1E" }, // vert sapin
  { x:   0, hex: "#FFFFFF" }, // neutre
  { x:  10, hex: "#8B0000" }, // rouge sang
];

const _hexToRgb = (hex) => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
];

const _lerp = (a, b, t) => Math.round(a + (b - a) * t);

const _mixHex = (hex1, hex2, t) => {
  const a = _hexToRgb(hex1);
  const b = _hexToRgb(hex2);
  return `rgb(${_lerp(a[0], b[0], t)}, ${_lerp(a[1], b[1], t)}, ${_lerp(a[2], b[2], t)})`;
};

/** Interpolation lineaire entre les 3 stops (vert -10, blanc 0, rouge +10).
 *  Saturation au-dela de +/- 10 %. Couleur du texte : navy pour les tons
 *  clairs (proches de 0), blanc pour les extremes (|var| > ~6 %) pour
 *  garantir la lisibilite sur les fonds sombres. */
function deltaStyle(varPct) {
  if (varPct == null || isNaN(varPct)) {
    return { backgroundColor: "#F5F3EE", color: C.mute };
  }
  // Saturation aux bornes
  if (varPct <= STOPS[0].x) {
    return { backgroundColor: STOPS[0].hex, color: "#FFFFFF" };
  }
  const last = STOPS[STOPS.length - 1];
  if (varPct >= last.x) {
    return { backgroundColor: last.hex, color: "#FFFFFF" };
  }
  // Interpolation dans l'intervalle encadrant
  let bg = "#FFFFFF";
  for (let i = 0; i < STOPS.length - 1; i++) {
    const a = STOPS[i], b = STOPS[i + 1];
    if (varPct >= a.x && varPct <= b.x) {
      const t = (varPct - a.x) / (b.x - a.x);
      bg = _mixHex(a.hex, b.hex, t);
      break;
    }
  }
  // Texte blanc si le fond est sombre (|var| > 6 % => proche des extremes)
  const color = Math.abs(varPct) >= 6 ? "#FFFFFF" : C.navy;
  return { backgroundColor: bg, color };
}

export default function PriceCorridor({
  current, min, max, avg,
  varD1, varW1, sigmaD,
}) {
  if (min == null || max == null || max <= min) {
    return (
      <div className="text-xs tabular-nums" style={{ color: C.navy }}>
        {fmt(current)}
      </div>
    );
  }

  const range = max - min;
  const clamp = (x) => Math.max(0, Math.min(100, x));
  const currPct = current != null ? clamp(((current - min) / range) * 100) : null;
  const avgPct  = avg     != null ? clamp(((avg     - min) / range) * 100) : null;

  // Couleur du point courant selon position dans la plage YTD
  let dotColor = C.navy;
  if (currPct != null) {
    if (currPct <= 33)      dotColor = C.green;
    else if (currPct >= 66) dotColor = C.gold;
  }

  return (
    <div
      className="corridor-cell w-full min-w-[360px] flex items-center gap-3"
      style={{ color: C.navy }}
      title={`Min ${fmt(min)} | Moy. ${fmt(avg)} | Max ${fmt(max)}${
        current != null ? ` | Actuel ${fmt(current)}` : ""
      }`}
    >
      {/* Colonne gauche : bullet chart (prix + track + min/max/moy) */}
      <div className="flex-1 min-w-[220px]">
        {/* Valeur actuelle flottante au-dessus du point */}
        <div className="relative h-4">
          {currPct != null && (
            <div
              className="absolute text-sm font-bold whitespace-nowrap tabular-nums"
              style={{
                left: `${currPct}%`,
                transform: "translateX(-50%)",
                bottom: 0,
                color: C.navy,
              }}
            >
              {fmt(current)}
            </div>
          )}
        </div>

        {/* Track + marqueurs */}
        <div className="relative h-2 rounded-full" style={{ backgroundColor: C.track }}>
          {avgPct != null && (
            <div
              className="absolute top-[-3px] w-[2px] h-[14px] rounded-sm"
              style={{
                left: `${avgPct}%`,
                transform: "translateX(-50%)",
                backgroundColor: C.mute,
                opacity: 0.75,
              }}
              title={`Moy. : ${fmt(avg)}`}
            />
          )}
          {currPct != null && (
            <div
              className="absolute top-[-3px] w-[14px] h-[14px] rounded-full"
              style={{
                left: `${currPct}%`,
                transform: "translateX(-50%)",
                backgroundColor: dotColor,
                border: "2px solid #FFFFFF",
                boxShadow: "0 1px 2px rgba(0,0,0,0.15)",
              }}
              title={`Actuel : ${fmt(current)}`}
            />
          )}
        </div>

        {/* Labels min / max / moy : masques par defaut, affiches
            au survol de la cellule ou lors d'un export PDF. Cf. index.css. */}
        <div className="corridor-details">
          <div className="flex justify-between text-[10px] mt-1 tabular-nums"
               style={{ color: C.mute }}>
            <span>Min&nbsp;{fmt(min)}</span>
            <span>Max&nbsp;{fmt(max)}</span>
          </div>
          <div className="text-center text-[10px] tabular-nums" style={{ color: C.mute }}>
            Moy.&nbsp;{fmt(avg)}
          </div>
        </div>
      </div>

      {/* Colonne droite : deltas J-1 / S-1 cote a cote, compactes */}
      <div className="flex gap-1.5 shrink-0">
        <div
          className="w-[78px] text-center text-[12px] font-semibold py-1.5 rounded-md tabular-nums"
          style={deltaStyle(varD1)}
          title={`Var J-1 : ${fmtPct(varD1)}`}
        >
          <span className="opacity-70 text-[11px] block leading-tight font-medium">J-1</span>
          {fmtPct(varD1)}
        </div>
        <div
          className="w-[78px] text-center text-[12px] font-semibold py-1.5 rounded-md tabular-nums"
          style={deltaStyle(varW1)}
          title={`Var S-1 : ${fmtPct(varW1)}`}
        >
          <span className="opacity-70 text-[11px] block leading-tight font-medium">S-1</span>
          {fmtPct(varW1)}
        </div>
      </div>
    </div>
  );
}
