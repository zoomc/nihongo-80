// Regression: untrusted POSTs must be rejected before parsing or touching D1.
import { createRequire } from 'node:module';
import { strict as assert } from 'node:assert';
const require = createRequire(new URL('../deploy/package.json', import.meta.url));
const { build } = require('esbuild');
const result = await build({entryPoints:[new URL('../deploy/worker/src/index.ts',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'browser'});
const worker = (await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'))).default;
const env = {NH80_SYNC_KEY:'test-only-key',DB:{prepare(){throw new Error('must not touch DB')}}};
const response = await worker.fetch(new Request('https://example.test/api/events',{method:'POST',body:'{}',headers:{'content-type':'application/json'}}),env);
assert.equal(response.status,401);
console.log('PASS: unauthenticated writes denied before database access');

// Smoke-check path must reach D1 and never store learning events.
let prepared = 0;
const env2 = {NH80_SYNC_KEY:'test-only-key',DB:{prepare(sql){prepared++;return{first:async()=>({id:'total'})}}}};
const res2 = await worker.fetch(new Request('https://example.test/api/events',{method:'POST',
  body:JSON.stringify({v:1,day:1,check:true}),headers:{'content-type':'application/json','X-NH80-Key':'test-only-key'}}),env2);
const body2 = await res2.json();
assert.equal(res2.status,200);
assert.equal(body2.ok,true);
assert.equal(body2.stored,0);
assert.equal(prepared,1);
console.log('PASS: authenticated check probes D1 without writing');
