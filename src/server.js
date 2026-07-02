const Fastify = require('fastify');
const fs = require('node:fs');
const path = require('node:path');
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

  app.post('/v1/chat', async (request, reply) => {
    const body = request.body || {};
    if (!body.message || typeof body.message !== 'string') {
      return reply.code(400).send({ error: 'message is required' });
    }

    const result = await generate({
      config,
      fetchImpl,
      model: body.model,
      system: body.system || 'You are a concise conversational assistant.',
      prompt: body.message,
      options: {
        temperature: body.temperature ?? 0.4,
      },
    });

    return {
      model: result.model || body.model || config.defaultModel,
      response: String(result.response || '').trim(),
    };
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

  app.post('/v1/depot-notes/generate', async (request, reply) => {
    const body = request.body || {};
    if (!body.transcript || typeof body.transcript !== 'string') {
      return reply.code(400).send({ error: 'transcript is required' });
    }

    const headings = Array.isArray(body.headings) ? body.headings.filter((item) => typeof item === 'string') : [];
    const exampleHints = retrieveDepotNoteExampleHints({
      transcript: body.transcript,
      examplesDir: config.depotNotesExamplesDir,
      limit: 3,
    });
    const prompt = buildDepotNotesPrompt({
      transcript: body.transcript,
      headings,
      exampleHints,
    });

    const result = await generate({
      config,
      fetchImpl,
      model: body.model,
      system: 'You generate concise depot-compatible job notes as strict JSON.',
      prompt,
      format: 'json',
      options: {
        temperature: body.temperature ?? 0,
      },
    });

    return {
      model: result.model || body.model || config.defaultModel,
      json: extractJsonObject(result.response),
      raw: result.response,
      examplesUsed: exampleHints.length,
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
      system: body.system || 'You summarise text accurately and concisely.',
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

function tokenize(text) {
  return Array.from(new Set(String(text || '').toLowerCase().match(/[a-z0-9]{3,}/g) || []));
}

function overlapScore(left, right) {
  const a = tokenize(left);
  const b = new Set(tokenize(right));
  return a.reduce((total, term) => total + (b.has(term) ? 1 : 0), 0);
}

function readDepotNoteExamples(examplesDir) {
  if (!examplesDir) return [];
  let entries;
  try {
    entries = fs.readdirSync(examplesDir, { withFileTypes: true });
  } catch {
    return [];
  }
  return entries
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith('.json'))
    .flatMap((entry) => {
      try {
        const filePath = path.join(examplesDir, entry.name);
        const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        return [parsed];
      } catch {
        return [];
      }
    })
    .filter((item) => item && typeof item.transcript === 'string');
}

function summarizeDepotNoteExample(example) {
  const sections = Array.isArray(example.sections) ? example.sections : [];
  const texts = sections.map((section) => String(section && section.text ? section.text : '')).filter(Boolean);
  const semicolonSections = texts.filter((text) => text.includes(';')).length;
  const notMentionedSections = texts.filter((text) => /^not mentioned$/i.test(text.trim())).length;
  const shortSections = texts.filter((text) => text.length <= 220).length;
  return {
    sectionCount: sections.length,
    usesSemicolonSeparators: semicolonSections > 0,
    shortPracticalSections: shortSections >= Math.max(1, Math.floor(texts.length * 0.6)),
    notMentionedSections,
  };
}

function retrieveDepotNoteExampleHints({ transcript, examplesDir, limit }) {
  return readDepotNoteExamples(examplesDir)
    .map((example) => ({
      score: overlapScore(transcript, example.transcript),
      summary: summarizeDepotNoteExample(example),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map((item) => item.summary);
}

function buildDepotNotesPrompt({ transcript, headings, exampleHints }) {
  const headingText = headings.length ? headings.join(' | ') : 'use the requested depot-note headings';
  const exampleText = exampleHints.length
    ? [
        'Closest stored example formatting patterns, derived without copying example content:',
        ...exampleHints.map((hint, index) => (
          `Example pattern ${index + 1}: ${hint.sectionCount} sections; `
          + `${hint.usesSemicolonSeparators ? 'uses ; separators' : 'does not consistently use ; separators'}; `
          + `${hint.shortPracticalSections ? 'keeps sections short' : 'sections may need shortening'}; `
          + `${hint.notMentionedSections} Not mentioned sections.`
        )),
      ].join('\n')
    : 'No stored depot-note examples matched this transcript.';
  return [
    'Create depot notes from the transcript.',
    'Return strict JSON only with this shape: {"sections":[{"heading":"...","text":"..."}]}',
    'Use exactly these headings and no others: ' + headingText,
    'Each generated section uses short practical bullets.',
    'Use ; as the line-break separator for depot compatibility.',
    'Keep text short enough for engineers to scan quickly.',
    'Avoid repeating generic T&Cs.',
    'Use "Not mentioned" only when there is no relevant job-specific information.',
    'Never invent information not present in the transcript.',
    exampleText,
    'Transcript:',
    transcript,
  ].join('\n');
}

module.exports = { buildServer };
