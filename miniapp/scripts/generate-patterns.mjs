// Pattern generator for master category backgrounds.
//
// Architecture: every category shares the SAME 26-slot scatter grid
// (POSITIONS). Each category provides 2 inline-SVG fragments
// (`big` and `small`) plugged into the slots. This guarantees:
//   1. Visual rhythm is identical across categories (designer-fixed)
//   2. Mixing two categories = alternate slots between A/B, never
//      "two full-density layers stacked", so no visual mess.
//
// A category can also provide an ARRAY for big/small — the generator
// then cycles through the variants across slots of that type. Used
// for the "other / stylist" pattern (curated multi-icon mix) and
// will be re-used for wiring 2-category masters.
//
// Run:   cd miniapp && node scripts/generate-patterns.mjs
// Output: miniapp/public/patterns/<slug>.svg per SHAPES key

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, '..', 'public', 'patterns');

// 26 positions — 9 "big" anchors + 17 "small" confetti.
const POSITIONS = [
  // big anchors (9)
  { x: 20, y: 10, rotate: -15, scale: 0.45, slot: 'big'   },
  { x: 45, y: 25, rotate:  35, scale: 0.38, slot: 'big'   },
  { x: 28, y: 48, rotate:   8, scale: 0.64, slot: 'big'   },
  { x:  8, y: 72, rotate:  30, scale: 0.50, slot: 'big'   },
  { x: 62, y: 70, rotate:  12, scale: 0.34, slot: 'big'   },
  { x: 78, y: 18, rotate:  28, scale: 0.64, slot: 'big'   },
  { x: 62, y: 38, rotate:  -8, scale: 0.53, slot: 'big'   },
  { x: 38, y: 62, rotate: -25, scale: 0.68, slot: 'big'   },
  { x: 82, y: 85, rotate:  20, scale: 0.53, slot: 'big'   },
  // small confetti (17)
  { x: 12, y: 32, rotate:  12, scale: 0.30, slot: 'small' },
  { x: 88, y: 42, rotate: -22, scale: 0.32, slot: 'small' },
  { x: 72, y: 55, rotate:  60, scale: 0.30, slot: 'small' },
  { x: 95, y: 65, rotate: -50, scale: 0.26, slot: 'small' },
  { x: 50, y: 80, rotate: -10, scale: 0.34, slot: 'small' },
  { x: 22, y: 92, rotate: -15, scale: 0.30, slot: 'small' },
  { x:  8, y: 18, rotate:  20, scale: 0.26, slot: 'small' },
  { x: 92, y:  8, rotate: -30, scale: 0.30, slot: 'small' },
  { x: 60, y:  8, rotate:  45, scale: 0.30, slot: 'small' },
  { x: 35, y: 18, rotate: -45, scale: 0.26, slot: 'small' },
  { x:  5, y: 52, rotate:   5, scale: 0.26, slot: 'small' },
  { x: 50, y: 35, rotate:  70, scale: 0.30, slot: 'small' },
  { x: 78, y: 75, rotate: -65, scale: 0.30, slot: 'small' },
  { x: 38, y: 92, rotate:  55, scale: 0.30, slot: 'small' },
  { x: 68, y: 95, rotate: -30, scale: 0.26, slot: 'small' },
  { x: 95, y: 30, rotate:  70, scale: 0.30, slot: 'small' },
  { x: 18, y:  5, rotate: -60, scale: 0.30, slot: 'small' },
];

// === Inline SVG fragments per category =====================================
// All fragments live in a 24x24 coordinate frame, center ~(12,12).

// nails
const NAILS_BIG   = '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>';
const NAILS_SMALL = '<path d="M12 2 L14.5 9.5 L22 12 L14.5 14.5 L12 22 L9.5 14.5 L2 12 L9.5 9.5 Z"/>';

// barber — scissors / comb
const BARBER_BIG   = '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M9 8 L20 19 M9 16 L20 5"/>';
const BARBER_SMALL = '<path d="M5 9h14M7 9v6M11 9v6M15 9v6M19 9v6"/>';

// pets — paw / small paw pad
const PETS_BIG   = '<circle cx="6" cy="9" r="2.4"/><circle cx="10.5" cy="6" r="2.4"/><circle cx="14.5" cy="6" r="2.4"/><circle cx="19" cy="9" r="2.4"/><ellipse cx="12.5" cy="16.5" rx="5" ry="4"/>';
const PETS_SMALL = '<ellipse cx="12" cy="13" rx="4" ry="3.5"/><circle cx="9" cy="8" r="1.5"/><circle cx="15" cy="8" r="1.5"/>';

// photo — camera / aperture
const PHOTO_BIG   = '<path d="M9 4l1.5 3h3L15 4z"/><rect x="3" y="7" width="18" height="14" rx="2"/><circle cx="12" cy="14" r="4"/>';
const PHOTO_SMALL = '<circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1.5"/>';

// garden — leaf / seedling-leaf
const GARDEN_BIG   = '<path d="M4 20c0-9 7-16 16-16 0 9-7 16-16 16zM4 20l9-9"/>';
const GARDEN_SMALL = '<path d="M6 14c0-4 3-7 7-7 0 4-3 7-7 7zM6 14l4-4"/>';

// clean — spray bottle / bubble
const CLEAN_BIG   = '<rect x="8" y="10" width="9" height="11" rx="1.5"/><path d="M11 10V6h4v4M15 8h3v2l-3 1"/>';
const CLEAN_SMALL = '<circle cx="12" cy="12" r="3.5"/>';

// upholstery — sofa / water drop
const UPHOLSTERY_BIG   = '<path d="M3 13v6h18v-6 M5 13V9a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4 M12 7v6 M5 19v2 M19 19v2"/>';
const UPHOLSTERY_SMALL = '<path d="M12 4c-3 3-5 6-5 9a5 5 0 0 0 10 0c0-3-2-6-5-9z"/>';

// massage — flower (5 circles) / small leaf
const MASSAGE_BIG   = '<circle cx="12" cy="12" r="2"/><circle cx="12" cy="6" r="2.5"/><circle cx="18" cy="12" r="2.5"/><circle cx="12" cy="18" r="2.5"/><circle cx="6" cy="12" r="2.5"/>';
const MASSAGE_SMALL = '<path d="M6 14c0-4 4-7 8-7 0 4-4 7-8 7z"/>';

// appliance — wrench / bolt
const APPLIANCE_BIG   = '<path d="M16 3a4 4 0 1 0 4 4l-3 3-4-4z M13 9L4 18l2 2 9-9"/>';
const APPLIANCE_SMALL = '<circle cx="12" cy="12" r="3"/><path d="M9 9l6 6"/>';

// handy — hammer / nail
const HANDY_BIG   = '<path d="M14 3l6 6-3 3-6-6z M11 6L4 13l3 3 7-7"/>';
const HANDY_SMALL = '<path d="M12 4l3 4h-1v10h-4V8H9z"/>';

// tutor — open book / star
const TUTOR_BIG   = '<path d="M3 6h7a2 2 0 0 1 2 2v12a1 1 0 0 0-1-1H3V6z M21 6h-7a2 2 0 0 0-2 2v12a1 1 0 0 1 1-1h8V6z"/>';
const TUTOR_SMALL = '<path d="M12 3l3 6 6 1-4 4 1 6-6-3-6 3 1-6-4-4 6-1z"/>';

// psy — speech bubble / 3 dots
const PSY_BIG   = '<path d="M5 4h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-9l-5 4V6a2 2 0 0 1 2-2z"/>';
const PSY_SMALL = '<circle cx="7" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="17" cy="12" r="1.5"/>';

// === Category map ==========================================================
const SHAPES = {
  nails:      { big: NAILS_BIG,      small: NAILS_SMALL      },
  barber:     { big: BARBER_BIG,     small: BARBER_SMALL     },
  pets:       { big: PETS_BIG,       small: PETS_SMALL       },
  photo:      { big: PHOTO_BIG,      small: PHOTO_SMALL      },
  garden:     { big: GARDEN_BIG,     small: GARDEN_SMALL     },
  clean:      { big: CLEAN_BIG,      small: CLEAN_SMALL      },
  upholstery: { big: UPHOLSTERY_BIG, small: UPHOLSTERY_SMALL },
  massage:    { big: MASSAGE_BIG,    small: MASSAGE_SMALL    },
  appliance:  { big: APPLIANCE_BIG,  small: APPLIANCE_SMALL  },
  handy:      { big: HANDY_BIG,      small: HANDY_SMALL      },
  tutor:      { big: TUTOR_BIG,      small: TUTOR_SMALL      },
  psy:        { big: PSY_BIG,        small: PSY_SMALL        },

  // Curated multi-icon mix for "stylist / other" master profile.
  // Generator cycles through the arrays across slots.
  other: {
    big:   [NAILS_BIG,   PHOTO_BIG,   GARDEN_BIG,   BARBER_BIG],
    small: [NAILS_SMALL, GARDEN_SMALL, BARBER_SMALL, PHOTO_SMALL],
  },
};

function generateSVG(categoryName) {
  const shapes = SHAPES[categoryName];
  if (!shapes) throw new Error(`Unknown category: ${categoryName}`);

  let bigIdx = 0, smallIdx = 0;
  const glyphs = POSITIONS.map((pos) => {
    const slotShapes = shapes[pos.slot];
    let shape;
    if (Array.isArray(slotShapes)) {
      const i = pos.slot === 'big' ? bigIdx++ : smallIdx++;
      shape = slotShapes[i % slotShapes.length];
    } else {
      shape = slotShapes;
    }
    return `    <g transform="translate(${pos.x} ${pos.y}) rotate(${pos.rotate}) scale(${pos.scale}) translate(-12 -12)">${shape}</g>`;
  }).join('\n');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <g stroke="black" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
${glyphs}
  </g>
</svg>
`;
}

fs.mkdirSync(OUT_DIR, { recursive: true });
for (const cat of Object.keys(SHAPES)) {
  fs.writeFileSync(path.join(OUT_DIR, `${cat}.svg`), generateSVG(cat));
  console.log(`✓ wrote ${cat}.svg`);
}
console.log(`\nDone. ${Object.keys(SHAPES).length} patterns in ${OUT_DIR}`);
