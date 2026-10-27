# Clavier virtuel de Fortinatus

Images créées le 16 octobre 2026 avec l’outil imagegen intégré. Les PNG originaux ont un canal alpha transparent et sont inclus dans l’application et les sources.

- `orbe-turquoise-v1.png` : adaptation turquoise de l’orbe de Transcrinator `Transcri/assets/hud-orange/core-hub-v1.png`, conservée comme image de référence.
- `frames/core-00.png` à `core-03.png` : images du projet Transcrinator, reprises à l’identique depuis `Transcri/assets/hud-orange/frames`. Fortinatus les colore en turquoise à l’affichage avec l’effet natif Qt, puis interpole les images toutes les 40 ms. L’orbe fait 36 × 36 pixels logiques sur chaque écran. Depuis 1.2.2, seul le cœur est animé : aucun anneau ni arc extérieur n’est dessiné. Les images `orbit-00.png` à `orbit-03.png` sont conservées comme références de l’ancienne version.
- `touche-v1.png` : concept initial de touche vierge, conservé avec son prompt. Depuis 1.2.1, les boutons utilisent une surface vectorielle continue avec dégradé et coins arrondis. Aucun découpage de texture ne crée de traits de raccord. Le texte reste indépendant et accessible.

## Prompt de l’orbe — édition de l’image de Transcrinator

Use case: precise-object-edit. Edit target: the attached amber energy orb from the Transcrinator app. Create the matching turquoise version for Fortinatus. Change ONLY the colors: replace amber, orange and yellow with brilliant turquoise, cyan and pale mint-white light, deeper areas in petrol teal. Preserve the same spherical silhouette, internal swirling energy ribbons, delicate filaments, central bright core, photographic polished glow, perspective, proportions, positioning and generous transparent margin. Keep all outside background truly transparent. No added frame, no symbols, no text, no icon badge. This is the companion orb that will sit directly above the original yellow one at 36 pixels.

## Prompt de la touche — nouvelle image

Use case: product-mockup. Asset type: one reusable final PNG skin for individual virtual keyboard keys in an elegant turquoise desktop app. Create a single blank square keyboard key cap, centered and front-facing, occupying 94 percent of square image. Deep petrol teal frosted glass face, extremely clean subtly beveled edges, rounded corners about 14 percent radius, refined hairline turquoise highlight along the top and side rims, very shallow dark raised bottom edge. Dark and sophisticated, not a toy, no busy texture, no saturated neon. The smooth flat center has generous clear space for a white character that will be drawn later by software. Truly transparent background around the silhouette; no external drop shadow. No text, no letters, no symbols, no additional objects, no keyboard array, no perspective tilt. Symmetrical rounded square with excellent readable simple silhouette when reduced to 48 pixels. Colors #0d252c, #143c43, #28656b, restrained #75cdbf highlights.
