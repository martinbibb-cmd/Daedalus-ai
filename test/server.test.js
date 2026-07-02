const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
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

test('self-test requires x-daedalus-api-key', async () => {
  const app = buildServer({ config, logger: false });
  const response = await app.inject({ method: 'GET', url: '/v1/self-test' });

  assert.equal(response.statusCode, 401);
});

test('self-test calls configured Ollama URL using default model', async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    assert.equal(url, 'http://ollama.test/api/generate');
    const body = JSON.parse(init.body);
    assert.equal(body.model, 'llama3.2:3b');
    assert.equal(body.stream, false);
    assert.match(body.prompt, /Daedalus LLM is working/);
    return jsonResponse({ model: body.model, response: 'Daedalus LLM is working.' });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'GET',
    url: '/v1/self-test',
    headers: { 'x-daedalus-api-key': 'test-secret' },
  });

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.json(), {
    ok: true,
    gateway: 'daedalus-llm-gateway',
    ollamaReachable: true,
    model: 'llama3.2:3b',
    generated: true,
    sample: 'Daedalus LLM is working.',
  });
  assert.equal(calls.length, 1);
});

test('self-test does not return secrets or public Ollama instructions on failure', async () => {
  const privateConfig = {
    ...config,
    ollamaBaseUrl: 'http://127.0.0.1:11434',
  };
  const fetchImpl = async () => {
    throw new Error('connect ECONNREFUSED http://127.0.0.1:11434 with test-secret');
  };
  const app = buildServer({ config: privateConfig, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'GET',
    url: '/v1/self-test',
    headers: { 'x-daedalus-api-key': 'test-secret' },
  });

  assert.equal(response.statusCode, 502);
  const body = response.json();
  assert.equal(body.ok, false);
  assert.equal(body.ollamaReachable, false);
  assert.equal(body.model, 'llama3.2:3b');

  const serialized = JSON.stringify(body);
  assert.equal(serialized.includes('test-secret'), false);
  assert.equal(serialized.includes('DAEDALUS_LLM_API_KEY'), false);
  assert.equal(serialized.includes(':11434'), false);
});

test('self-test does not call api.openai.com', async () => {
  const urls = [];
  const fetchImpl = async (url, init) => {
    urls.push(url);
    assert.equal(String(url).includes('api.openai.com'), false);
    const body = JSON.parse(init.body);
    return jsonResponse({ model: body.model, response: 'Daedalus LLM is working.' });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'GET',
    url: '/v1/self-test',
    headers: { 'x-daedalus-api-key': 'test-secret' },
  });

  assert.equal(response.statusCode, 200);
  assert.deepEqual(urls, ['http://ollama.test/api/generate']);
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

test('chat route calls Ollama with conversational prompt', async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'http://ollama.test/api/generate');
    const body = JSON.parse(init.body);
    assert.equal(body.model, 'llama3.2:3b');
    assert.equal(body.prompt, 'Hello');
    assert.equal(body.system, 'You are concise.');
    assert.equal(body.options.temperature, 0.7);
    assert.equal(body.stream, false);
    return jsonResponse({ model: body.model, response: 'Hi. How can I help?' });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'POST',
    url: '/v1/chat',
    headers: { 'x-daedalus-api-key': 'test-secret' },
    payload: {
      message: 'Hello',
      system: 'You are concise.',
      temperature: 0.7,
    },
  });

  assert.equal(response.statusCode, 200);
  assert.equal(response.json().response, 'Hi. How can I help?');
});

test('summarise route allows a caller-provided system prompt', async () => {
  const fetchImpl = async (url, init) => {
    assert.equal(url, 'http://ollama.test/api/generate');
    const body = JSON.parse(init.body);
    assert.equal(body.system, 'You are a conversational assistant.');
    assert.match(body.prompt, /Reply naturally/);
    assert.match(body.prompt, /Hey how are you/);
    return jsonResponse({ model: body.model, response: 'I am doing well. How can I help?' });
  };
  const app = buildServer({ config, fetchImpl, logger: false });

  const response = await app.inject({
    method: 'POST',
    url: '/v1/summarise',
    headers: { 'x-daedalus-api-key': 'test-secret' },
    payload: {
      text: 'Hey how are you?',
      system: 'You are a conversational assistant.',
      instruction: 'Reply naturally.',
    },
  });

  assert.equal(response.statusCode, 200);
  assert.equal(response.json().summary, 'I am doing well. How can I help?');
});

test('manual guide UI clears chat input after send', () => {
  const worker = fs.readFileSync(path.join(__dirname, '..', 'src', 'worker.js'), 'utf8');

  assert.match(worker, /const text = question\.value\.trim\(\);[\s\S]*question\.value = "";/);
  assert.match(worker, /fetch\("\/manuals\/query"/);
});

test('manual guide UI preserves follow-up chat history', () => {
  const worker = fs.readFileSync(path.join(__dirname, '..', 'src', 'worker.js'), 'utf8');

  assert.match(worker, /history: JSON\.parse\(sessionStorage\.getItem\("boilerGuideHistory"\)/);
  assert.match(worker, /state\.history\.push\(userTurn\)/);
  assert.match(worker, /for \(const turn of state\.history\)/);
});
