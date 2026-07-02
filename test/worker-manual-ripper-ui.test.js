const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { handleRequest } = require('../src/worker');

const workerSource = fs.readFileSync(path.join(__dirname, '..', 'src', 'worker.js'), 'utf8');

test('manual ripper clears input after send and preserves chat history', () => {
  assert.match(workerSource, /state\.manualHistory = \[\]/);
  assert.match(workerSource, /appendManualMessage\("user", question \|\| "Attached photographed manual page\."\)/);
  assert.match(workerSource, /els\.prompt\.value = ""/);
  assert.match(workerSource, /state\.manualHistory\.push\(\{ role: "assistant"/);
});

test('manual ripper supports photographed page attachment without guessing', () => {
  assert.match(workerSource, /id="manual-image"/);
  assert.match(workerSource, /accept="image\/\*"/);
  assert.match(workerSource, /\/query-image"/);
  assert.match(workerSource, /formData\.append\("image", image\)/);
});

test('manual ripper renders citations and evidence images', () => {
  assert.match(workerSource, /className = "manual-citations"/);
  assert.match(workerSource, /className = "manual-evidence-grid"/);
  assert.match(workerSource, /document\.createElement\("img"\)/);
  assert.match(workerSource, /target = "_blank"/);
});

test('manual proxy passes visual assets through as binary responses', () => {
  assert.match(workerSource, /!upstreamType\.includes\("application\/json"\)/);
  assert.match(workerSource, /new Response\(upstream\.body/);
});

test('public welcome page is served at root', async () => {
  const response = await handleRequest(new Request('https://example.test/'), {});
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /The Hitchhiker's Guide to Boilers/);
  assert.match(html, /DON'T PANIC/);
  assert.match(html, /href="\/chat"/);
});

test('public chat page searches all manuals without a manual selector', async () => {
  const response = await handleRequest(new Request('https://example.test/chat'), {});
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /fetch\("\/manuals\/query"/);
  assert.doesNotMatch(html, /manual-list/);
  assert.match(html, /sessionStorage/);
});

test('dev page contains the existing full console behind admin gate', async () => {
  const denied = await handleRequest(new Request('https://example.test/dev'), { ADMIN_KEY: 'secret' });
  assert.equal(denied.status, 401);

  const response = await handleRequest(
    new Request('https://example.test/dev', { headers: { 'x-admin-key': 'secret' } }),
    { ADMIN_KEY: 'secret' },
  );
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /AI Gateway Engineering Console/);
  assert.match(html, /Manual Ripper/);
  assert.match(html, /Raw request JSON/);
});

test('admin route is present and key gated', async () => {
  const denied = await handleRequest(new Request('https://example.test/admin'), { ADMIN_KEY: 'secret' });
  assert.equal(denied.status, 401);

  const response = await handleRequest(
    new Request('https://example.test/admin?admin_key=secret'),
    { ADMIN_KEY: 'secret' },
  );
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /Document Manager/);
  assert.match(html, /Upload PDF/);
  assert.match(html, /Stored Documents/);
});
