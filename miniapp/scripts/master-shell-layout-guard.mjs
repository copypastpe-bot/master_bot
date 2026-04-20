import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';

const root = resolve(import.meta.dirname, '..');

function read(relPath) {
  return readFileSync(resolve(root, relPath), 'utf8');
}

const masterApp = read('src/master/MasterApp.jsx');
const orderCreate = read('src/master/pages/OrderCreate.jsx');
const clientCard = read('src/master/pages/ClientCard.jsx');
const orderDetail = read('src/master/pages/OrderDetail.jsx');

assert.match(
  masterApp,
  /const rootTitleMap = \{/,
  'Root tab title mapping is missing in MasterApp',
);

assert.match(
  masterApp,
  /const currentTitle = current \? \(titleMap\[current\.type\] \?\? 'Master_bot'\) : rootTitleMap\[tab\];/,
  'MasterApp still does not derive the header title from the active root tab',
);

assert.doesNotMatch(
  orderCreate,
  /\bautoFocus\b/,
  'OrderCreate still auto-focuses the client search input',
);

assert.match(
  orderCreate,
  /enabled: true,/,
  'OrderCreate still does not request the initial client list before typing',
);

assert.match(
  clientCard,
  /className="master-detail-page client-card-page"/,
  'ClientCard is not using the shared full-width detail layout class',
);

assert.match(
  orderDetail,
  /className="master-detail-page order-detail-page"/,
  'OrderDetail is not using the shared full-width detail layout class',
);

console.log('master-shell layout guard passed');
