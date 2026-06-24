const Fastify = require('fastify');
const { extractJsonObject, generate, listModels } = require('./ollama');

function sanitizeDiagnosticError(error, config) {
  let message = error && error.message ? error.message : 'Ollama self-test failed';

  const redactions = [
    config.apiKey,
    config.ollamaBaseUrl,
    'api.openai.com',
  ].filter(Boolean);

  for (const value of redactions) {
    message = message.split(value).join('[redacted]');
  }

  return message.replace(/:11434\b/g, ':[redacted]');
}

function buildServer({ config, fetchImpl = fetch, logger = true }) {
  const app = Fastify({ logger });

  app.addHook('preHandler', async (request, reply) => {
    if (request.routeOptions.url === '/health') {
      return;
    }

    const apiKey = request.headers['x-daedalus-api-key'];
    if (apiKey !== config.apiKey) {
      return reply.code(401).send({ error: 'Unauthorized' });
    }
  });

  app.get('/health', async () => ({
    ok: true,
    service: 'daedalus-llm-gateway',
    defaultModel: config.defaultModel,
  }));

  app.get('/models', async () => listModels({ config, fetchImpl }));

  app.get('/v1/self-test', async (request, reply) => {
    try {
      const result = await generate({
        config,
        fetchImpl,
        prompt: 'Reply with this exact sentence and nothing else: Daedalus LLM is working.',
        system: 'You are a concise diagnostic check.',
        options: {
          temperature: 0,
        },
      });

      const sample = String(result.response || '').trim();
      if (!sample) {
        throw new Error('Ollama returned an empty response');
      }

      return {
        ok: true,
        gateway: 'daedalus-llm-gateway',
        ollamaReachable: true,
        model: result.model || config.defaultModel,
        generated: true,
        sample,
      };
    } catch (error) {
      return reply.code(502).send({
        ok: false,
        ollamaReachable: false,
        model: config.defaultModel,
        error: sanitizeDiagnosticError(error, config),
      });
    }
  });

  app.post('/v1/json', async (request, reply) => {
    const body = request.body || {};
    if (!body.prompt || typeof body.prompt !== 'string') {
      return reply.code(400).send({ error: 'prompt is required' });
    }

    const schemaInstruction = body.schema
      ? `\nReturn JSON matching this schema/shape only:\n${JSON.stringify(body.schema)}`
      : '\nReturn only valid JSON. Do not wrap it in markdown.';

    const result = await generate({
      config,
      fetchImpl,
      model: body.model,
      system: body.system || 'You are a precise JSON API. Return only valid JSON.',
      prompt: `${body.prompt}${schemaInstruction}`,
      format: 'json',
      options: {
        temperature: body.temperature ?? 0,
      },
    });

    return {
      model: result.model || body.model || config.defaultModel,
      json: extractJsonObject(result.response),
      raw: result.response,
    };
  });

  app.post('/v1/summarise', async (request, reply) => {
    const body = request.body || {};
    if (!body.text || typeof body.text !== 'string') {
      return reply.code(400).send({ error: 'text is required' });
    }

    const maxWords = Number.isFinite(body.maxWords) ? body.maxWords : 180;
    const instruction = body.instruction || `Summarise the text in no more than ${maxWords} words.`;

    const result = await generate({
      config,
      fetchImpl,
      model: body.model,
      system: 'You summarise text accurately and concisely.',
      prompt: `${instruction}\n\nText:\n${body.text}`,
      options: {
        temperature: body.temperature ?? 0.2,
      },
    });

    return {
      model: result.model || body.model || config.defaultModel,
      summary: String(result.response || '').trim(),
    };
  });

  app.post('/v1/extract-evidence', async (request, reply) => {
    const body = request.body || {};
    if (!body.text || typeof body.text !== 'string') {
      return reply.code(400).send({ error: 'text is required' });
    }

    const question = body.question || 'Extract the key claims and supporting evidence from the text.';
    const result = await generate({
      config,
      fetchImpl,
      model: body.model,
      system: 'You extract evidence from text. Return only valid JSON.',
      prompt: [
        question,
        '',
        'Return JSON with this shape only:',
        '{"claims":[{"claim":"string","evidence":["string"],"confidence":"low|medium|high"}]}',
        '',
        'Text:',
        body.text,
      ].join('\n'),
      format: 'json',
      options: {
        temperature: body.temperature ?? 0,
      },
    });

    return {
      model: result.model || body.model || config.defaultModel,
      json: extractJsonObject(result.response),
      raw: result.response,
    };
  });

  app.setErrorHandler((error, request, reply) => {
    request.log.error(error);
    reply.code(502).send({ error: error.message });
  });

  return app;
}

module.exports = { buildServer };
