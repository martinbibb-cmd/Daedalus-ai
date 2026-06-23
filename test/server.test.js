const test = require('node:test');
const assert = require('node:assert/strict');
const { buildServer } = require('../src/server');

const config = {
  apiKey: 'test-secret',
  ollamaBaseUrl: 'http://ollama.test',
  defaultModel: 'llama3.2:3b',
};

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

test('health does not require auth', async () => {
  const app = buildServer({ config, logger: false });
  const response = await app.inject({ method: 'GET', url: '/health' });

  assert.equal(response.statusCode, 200);
  assert.equal(response.json().ok, true);
});

test('protected routes require x-daedalus-api-key', async () => {
  const app = buildServer({ config, logger: false });
  const response = await app.inject({ method: 'GET', url: '/models' });

  assert.equal(response.statusCode, 401);
});

test('models proxies Ollama tags', async () => {
  const fetchImpl = async (url) => {
    assert.equal(url, 'http://ollama.test/api/tags');
    return jsonResponse({ models: [{ name: 'llama3.2:3b' }] });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'GET',
    url: '/models',
    headers: { 'x-daedalus-api-key': 'test-secret' },
  });

  assert.equal(response.statusCode, 200);
  assert.equal(response.json().defaultModel, 'llama3.2:3b');
  assert.equal(response.json().models[0].name, 'llama3.2:3b');
});

test('json route returns parsed model JSON', async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'http://ollama.test/api/generate');
    const body = JSON.parse(init.body);
    assert.equal(body.model, 'llama3.2:3b');
    assert.equal(body.stream, false);
    assert.equal(body.format, 'json');
    return jsonResponse({ model: body.model, response: '{"answer":42}' });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'POST',
    url: '/v1/json',
    headers: { 'x-daedalus-api-key': 'test-secret' },
    payload: { prompt: 'Return the answer.' },
  });

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.json().json, { answer: 42 });
});

