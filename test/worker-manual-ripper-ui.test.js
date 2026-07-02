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

test('depot notes page renders editable section cards instead of one blob', async () => {
  const response = await handleRequest(new Request('https://example.test/depot-notes'), {});
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /Depot Notes/);
  assert.match(html, /Safe access at height/);
  assert.match(html, /Installer notes \u2014 boiler\/controls/);
  assert.match(html, /Copy/);
  assert.match(html, /Request changes to this section/);
  assert.match(html, /Apply change/);
  assert.match(html, /No depot notes generated yet/);
  assert.match(html, /Endpoint: /);
  assert.doesNotMatch(html, /one giant combined text block/);
});

test('depot notes endpoints require gateway configuration', async () => {
  const response = await handleRequest(
    new Request('https://example.test/depot-notes/generate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ transcript: 'Customer says scaffold is required.' }),
    }),
    {},
  );

  assert.equal(response.status, 500);
  assert.equal((await response.json()).error, 'LLM gateway is not configured');
});

test('depot notes generation uses supported json gateway endpoint', async () => {
  const originalFetch = global.fetch;
  let calledPath = '';
  let requestBody = null;
  global.fetch = async (url, init) => {
    calledPath = new URL(url).pathname;
    requestBody = JSON.parse(init.body);
    return new Response(
      JSON.stringify({
        json: {
          sections: [
            {
              heading: 'Safe access at height',
              text: 'Tower required for high flue; customer confirmed side gate access',
            },
          ],
        },
      }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  };

  try {
    const response = await handleRequest(
      new Request('https://example.test/depot-notes/generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ transcript: 'Customer confirmed tower required for high flue and side gate access.' }),
      }),
      {
        DAEDALUS_LLM_GATEWAY_URL: 'https://gateway.example',
        DAEDALUS_LLM_API_KEY: 'test-key',
        DAEDALUS_LLM_MODEL: 'test-model',
      },
    );
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(calledPath, '/v1/json');
    assert.equal(requestBody.prompt.includes('Customer confirmed tower required'), true);
    assert.equal(body.sections[0].heading, 'Safe access at height');
    assert.equal(body.sections[0].text, 'Tower required for high flue; customer confirmed side gate access');
  } finally {
    global.fetch = originalFetch;
  }
});

test('depot notes generation reports endpoint diagnostics on gateway failure', async () => {
  const originalFetch = global.fetch;
  global.fetch = async () => new Response(JSON.stringify({ error: 'route not found' }), { status: 404 });

  try {
    const response = await handleRequest(
      new Request('https://example.test/depot-notes/generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ transcript: 'Customer confirmed tower access.' }),
      }),
      {
        DAEDALUS_LLM_GATEWAY_URL: 'https://gateway.example',
        DAEDALUS_LLM_API_KEY: 'test-key',
        DAEDALUS_LLM_MODEL: 'test-model',
      },
    );
    const body = await response.json();

    assert.equal(response.status, 404);
    assert.equal(body.endpoint, '/v1/json');
    assert.equal(body.status, 404);
    assert.match(body.diagnostic, /gateway supports \/v1\/json/);
  } finally {
    global.fetch = originalFetch;
  }
});

test('public chat keeps manual context for ambiguous follow-ups', async () => {
  const response = await handleRequest(new Request('https://example.test/chat'), {});
  const html = await response.text();

  assert.match(html, /boilerGuideContext/);
  assert.match(html, /current_manual_id/);
  assert.match(html, /function rewriteQuestion/);
  assert.match(html, /appliance weight lift weight/);
  assert.match(html, /fetch\("\/manuals\/" \+ encodeURIComponent\(manualId\) \+ "\/query"/);
  assert.match(html, /I could not find relevant evidence for that in the selected\/manual context/);
});
