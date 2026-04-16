# Cockpit ACT Energy — Note sur les donnees manquantes

**Date** : 16 avril 2026
**De** : Equipe technique ACT Energy
**Pour** : Direction

---

## En resume

Quatre courbes de prix dans la section "Market Prices & Trends" du Cockpit
n'affichent des donnees que depuis debut avril 2026 au lieu de janvier 2026 :

- **BE M+1** (electricite, mois suivant)
- **BE Q+1** (electricite, trimestre suivant)
- **TTF M+1** (gaz, mois suivant)
- **TTF Q+1** (gaz, trimestre suivant)

**Les huit autres courbes (Y+1, Y+2, Y+3 et Q+2) sont completes depuis janvier.**

Ce n'est pas un bug. C'est une limitation de la source de donnees.

---

## Pourquoi ces donnees ne sont pas disponibles ?

### L'analogie simple

Imaginez un tableau d'affichage dans un aeroport qui montre les vols des
3 prochaines heures. Si vous arrivez a 15h, vous voyez les vols de 15h a 18h.
Mais les vols de 9h du matin ont disparu du tableau — ils sont partis et
l'affichage ne les montre plus.

C'est exactement ce qui se passe avec les prix de l'energie :

- En **janvier 2026**, le prix "mois suivant" (M+1) correspondait au contrat
  **fevrier 2026**. Ce prix etait visible et cotait chaque jour.
- En **avril 2026**, le contrat fevrier 2026 est **expire** — il a ete livre.
  Il n'apparait plus nulle part dans les fichiers de Luminus.
- Le fichier Luminus d'aujourd'hui ne contient que les contrats **encore en vie**
  (mai, juin, juillet 2026).

### En image

```
Janvier 2026 :  M+1 = FEV 2026  (prix visible)
Fevrier 2026 :  M+1 = MAR 2026  (prix visible)
Mars 2026    :  M+1 = AVR 2026  (prix visible)
Avril 2026   :  M+1 = MAI 2026  (prix visible)  <-- on est ici

Fichier telecharge aujourd'hui :
  MAI 2026 ✅  JUN 2026 ✅  JUL 2026 ✅
  FEV 2026 ❌  MAR 2026 ❌  AVR 2026 ❌  (expires, retires du fichier)
```

Le meme probleme s'applique au trimestre suivant (Q+1) :
le contrat Q2-2026 (avril-juin) est devenu le trimestre **en cours** et
n'est plus cote comme "futur".

---

## Quelles courbes sont completes ?

| Produit | Donnees disponibles | Raison |
|---------|-------------------|--------|
| Y+1, Y+2, Y+3 | ✅ Depuis janvier 2026 | Les contrats annuels (Cal 2027, 2028, 2029) sont a long terme et restent dans le fichier pendant des annees |
| Q+2 | ✅ Depuis janvier 2026 | Le trimestre Q+2 est assez eloigne pour ne pas expirer dans la fenetre |
| **M+1** | ❌ Depuis avril seulement | Le contrat mensuel expire chaque mois |
| **Q+1** | ❌ Depuis avril seulement | Le contrat trimestriel expire chaque trimestre |

---

## Comment on resout le probleme ?

Le Cockpit telecharge automatiquement les fichiers Luminus **chaque soir a
19h30** via un processus automatise (GitHub Actions). Chaque jour, le prix
M+1 et Q+1 du moment est enregistre et conserve dans notre historique.

**A partir de maintenant, les courbes M+1 et Q+1 se remplissent jour apres
jour.** D'ici quelques semaines, elles seront suffisamment longues pour etre
lisibles.

En revanche, les donnees de janvier a mars 2026 sont **definitivement
irrecuperables** pour M+1 et Q+1 — elles n'existent plus chez Luminus.

---

## Impact pour les clients

**Aucun impact sur le tableau Statistics** : toutes les valeurs (Var D-1, Var W-1,
Avg, Max, Min) sont correctes et completes.

**Impact visuel uniquement** sur 2 des 4 graphiques (FWB Elec et FWB Gaz) :
les courbes M+1 et Q+1 demarrent en avril au lieu de janvier. Cela se resorbera
naturellement avec le temps.

---

*Document genere le 16/04/2026 — Cockpit ACT Energy v1.0*
