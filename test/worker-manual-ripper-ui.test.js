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
  assert.match(html, /Health and safety observations/);
  assert.match(html, /Customer summary email/);
  assert.match(html, /Suggested follow-up diary entry/);
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

test('depot notes generation uses dedicated gateway endpoint', async () => {
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
    assert.equal(calledPath, '/v1/depot-notes/generate');
    assert.equal(requestBody.transcript.includes('Customer confirmed tower required'), true);
    assert.equal(Array.isArray(requestBody.headings), true);
    assert.equal(body.sections[0].heading, 'Safe access at height');
    assert.equal(body.sections[0].text, 'Tower required for high flue; customer confirmed side gate access');
  } finally {
    global.fetch = originalFetch;
  }
});

test('depot notes generation falls back to json endpoint for older gateways', async () => {
  const originalFetch = global.fetch;
  const calledPaths = [];
  global.fetch = async (url) => {
    const pathname = new URL(url).pathname;
    calledPaths.push(pathname);
    if (pathname === '/v1/depot-notes/generate') {
      return new Response(JSON.stringify({ error: 'not found' }), { status: 404 });
    }
    return new Response(
      JSON.stringify({
        json: {
          sections: [
            {
              heading: 'Safe access at height',
              text: 'Tower required',
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
        body: JSON.stringify({ transcript: 'Customer confirmed tower required.' }),
      }),
      {
        DAEDALUS_LLM_GATEWAY_URL: 'https://gateway.example',
        DAEDALUS_LLM_API_KEY: 'test-key',
        DAEDALUS_LLM_MODEL: 'test-model',
      },
    );

    assert.equal(response.status, 200);
    assert.deepEqual(calledPaths, ['/v1/depot-notes/generate', '/v1/json']);
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
    assert.equal(body.failureKind, 'route_missing');
    assert.match(body.diagnostic, /does not serve \/v1\/json/);
  } finally {
    global.fetch = originalFetch;
  }
});

test('depot notes generation reports upstream timeout separately', async () => {
  const originalFetch = global.fetch;
  global.fetch = async () => new Response(JSON.stringify({ error: 'Timeout' }), { status: 504 });

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

    assert.equal(response.status, 504);
    assert.equal(body.endpoint, '/v1/depot-notes/generate');
    assert.equal(body.failureKind, 'upstream_timeout');
    assert.match(body.diagnostic, /upstream model timed out/);
  } finally {
    global.fetch = originalFetch;
  }
});

test('depot notes debug reports route and configured model without secrets', async () => {
  const originalFetch = global.fetch;
  const calls = [];
  global.fetch = async (url) => {
    const pathname = new URL(url).pathname;
    calls.push(pathname);
    if (pathname.endsWith('/health')) {
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }
    if (pathname.endsWith('/models')) {
      return new Response(JSON.stringify({ defaultModel: 'test-model', models: [{ name: 'test-model' }] }), { status: 200 });
    }
    if (pathname.endsWith('/v1/depot-notes/generate')) {
      return new Response(JSON.stringify({ json: { ok: true } }), { status: 200 });
    }
    return new Response(JSON.stringify({ error: 'not found' }), { status: 404 });
  };

  try {
    const response = await handleRequest(
      new Request('https://example.test/depot-notes/debug'),
      {
        ADMIN_KEY: 'secret',
        DAEDALUS_LLM_GATEWAY_URL: 'https://gateway.example/private',
        DAEDALUS_LLM_API_KEY: 'test-key',
        DAEDALUS_LLM_MODEL: 'test-model',
      },
    );
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.ok, true);
    assert.equal(body.route, '/v1/depot-notes/generate');
    assert.equal(body.config.gatewayOrigin, 'https://gateway.example');
    assert.equal(body.config.apiKeyConfigured, true);
    assert.equal(body.config.model, 'test-model');
    assert.equal(body.models.configuredModelAvailable, true);
    assert.deepEqual(calls, ['/private/health', '/private/models', '/private/v1/depot-notes/generate']);
    assert.doesNotMatch(JSON.stringify(body), /test-key/);
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
