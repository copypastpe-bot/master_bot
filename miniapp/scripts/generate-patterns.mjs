// Pattern generator for master category backgrounds.
//
// Architecture: every category shares the SAME 26-slot scatter grid
// (POSITIONS). Each category just provides 2 inline-SVG fragments
// (`big` and `small`) plugged into the slots. This guarantees:
//   1. Visual rhythm is identical across categories (designer-fixed)
//   2. Mixing two categories = alternate slots between A/B, never
//      "two full-density layers stacked", so no visual mess.
//
// Run:   cd miniapp && node scripts/generate-patterns.mjs
// Output: miniapp/public/patterns/<slug>.svg for each SHAPES key

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, '..', 'public', 'patterns');

// 26 positions — 9 "big" anchors + 17 "small" confetti — Y-coords
// spread across full 0–100 range so tile repeats don't form rows.
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
  // small confetti fill (17)
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

// Each category provides two inline SVG fragments designed to fit in a
// 24x24 viewBox (center ~12,12). They're stamped into POSITIONS via
// `translate(x y) rotate(deg) scale(s) translate(-12 -12)`.
const SHAPES = {
  nails: {
    big:   '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>',
    small: '<path d="M12 2 L14.5 9.5 L22 12 L14.5 14.5 L12 22 L9.5 14.5 L2 12 L9.5 9.5 Z"/>',
  },
  barber: {
    // scissors: two handle circles + crossing blades
    big:   '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M9 8 L20 19 M9 16 L20 5"/>',
    // comb: bar with 4 teeth
    small: '<path d="M5 9h14M7 9v6M11 9v6M15 9v6M19 9v6"/>',
  },
  pets: {
    // paw print: 4 toes (circles) + main pad (ellipse)
    big:   '<circle cx="6" cy="9" r="2.4"/><circle cx="10.5" cy="6" r="2.4"/><circle cx="14.5" cy="6" r="2.4"/><circle cx="19" cy="9" r="2.4"/><ellipse cx="12.5" cy="16.5" rx="5" ry="4"/>',
    // tiny paw pad
    small: '<ellipse cx="12" cy="13" rx="4" ry="3.5"/><circle cx="9" cy="8" r="1.5"/><circle cx="15" cy="8" r="1.5"/>',
  },
  photo: {
    // camera: body rect + lens circle + viewfinder bump
    big:   '<path d="M9 4l1.5 3h3L15 4z"/><rect x="3" y="7" width="18" height="14" rx="2"/><circle cx="12" cy="14" r="4"/>',
    // tiny aperture / lens dot
    small: '<circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1.5"/>',
  },
  garden: {
    // leaf: classic curved leaf with central vein
    big:   '<path d="M4 20c0-9 7-16 16-16 0 9-7 16-16 16zM4 20l9-9"/>',
    // tiny seed/leaflet
    small: '<path d="M6 14c0-4 3-7 7-7 0 4-3 7-7 7zM6 14l4-4"/>',
  },
};

function generateSVG(categoryName) {
  const shapes = SHAPES[categoryName];
  if (!shapes) throw new Error(`Unknown category: ${categoryName}`);

  const glyphs = POSITIONS.map((pos) =>
    `    <g transform="translate(${pos.x} ${pos.y}) rotate(${pos.rotate}) scale(${pos.scale}) translate(-12 -12)">${shapes[pos.slot]}</g>`
  ).join('\n');

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
