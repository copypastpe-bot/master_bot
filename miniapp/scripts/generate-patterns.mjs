// CLI: regenerate all static category pattern SVGs from the shared
// patternData module. Single source of truth lives in src/.
//
// Run:   cd miniapp && node scripts/generate-patterns.mjs
// Output: miniapp/public/patterns/<slug>.svg per SHAPES key

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { SHAPES, buildSinglePatternSVG } from '../src/master/patterns/patternData.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, '..', 'public', 'patterns');

fs.mkdirSync(OUT_DIR, { recursive: true });

// Clean stale files (older filenames from earlier iterations).
for (const f of fs.readdirSync(OUT_DIR)) {
  if (f.endsWith('.svg')) fs.unlinkSync(path.join(OUT_DIR, f));
}

for (const slug of Object.keys(SHAPES)) {
  fs.writeFileSync(path.join(OUT_DIR, `${slug}.svg`), buildSinglePatternSVG(slug));
  console.log(`✓ wrote ${slug}.svg`);
}
console.log(`\nDone. ${Object.keys(SHAPES).length} patterns in ${OUT_DIR}`);
