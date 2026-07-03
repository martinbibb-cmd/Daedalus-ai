async function readJsonResponse(response) {
  const text = await response.text();

  if (!response.ok) {
    const detail = text ? `: ${text}` : '';
    throw new Error(`Ollama request failed with ${response.status}${detail}`);
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`Ollama returned invalid JSON: ${error.message}`);
  }
}

async function readProviderJsonResponse(response, providerName) {
  const text = await response.text();

  if (!response.ok) {
    const detail = text ? `: ${text}` : '';
    throw new Error(`${providerName} request failed with ${response.status}${detail}`);
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${providerName} returned invalid JSON: ${error.message}`);
  }
}

function extractJsonObject(text) {
  if (!text || typeof text !== 'string') {
    throw new Error('Model response was empty');
  }

  try {
    return JSON.parse(text);
  } catch {
    const firstBrace = text.indexOf('{');
    const lastBrace = text.lastIndexOf('}');

    if (firstBrace === -1 || lastBrace === -1 || lastBrace <= firstBrace) {
      throw new Error('Model response did not contain a JSON object');
    }

    return JSON.parse(text.slice(firstBrace, lastBrace + 1));
  }
}

async function listModels({ config, fetchImpl = fetch }) {
  if (config.provider === 'gemini') {
    return {
      defaultModel: config.defaultModel,
      provider: 'gemini',
      models: [{ name: config.defaultModel }],
    };
  }

  const response = await fetchImpl(`${config.ollamaBaseUrl}/api/tags`);
  const body = await readJsonResponse(response);

  return {
    defaultModel: config.defaultModel,
    models: Array.isArray(body.models) ? body.models : [],
  };
}

async function generate({ config, fetchImpl = fetch, model, prompt, system, format, options }) {
  if (config.provider === 'gemini') {
    return generateGemini({ config, fetchImpl, model, prompt, system, format, options });
  }

  const response = await fetchImpl(`${config.ollamaBaseUrl}/api/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      model: model || config.defaultModel,
      prompt,
      system,
      format,
      options,
      stream: false,
    }),
  });

  return readJsonResponse(response);
}

async function generateGemini({ config, fetchImpl = fetch, model, prompt, system, format, options }) {
  const selectedModel = model || config.defaultModel;
  const generationConfig = {
    temperature: options && Number.isFinite(options.temperature) ? options.temperature : 0,
  };
  if (format === 'json') {
    generationConfig.responseMimeType = 'application/json';
  }

  const response = await fetchImpl(`${config.geminiBaseUrl}/models/${encodeURIComponent(selectedModel)}:generateContent`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'X-goog-api-key': config.geminiApiKey,
    },
    body: JSON.stringify({
      systemInstruction: system ? { parts: [{ text: system }] } : undefined,
      contents: [
        {
          role: 'user',
          parts: [{ text: prompt }],
        },
      ],
      generationConfig,
    }),
  });

  const body = await readProviderJsonResponse(response, 'Gemini');
  const responseText = Array.isArray(body.candidates)
    ? body.candidates
        .flatMap((candidate) => candidate && candidate.content && Array.isArray(candidate.content.parts) ? candidate.content.parts : [])
        .map((part) => typeof part.text === 'string' ? part.text : '')
        .join('')
        .trim()
    : '';

  return {
    model: selectedModel,
    response: responseText,
    raw: body,
  };
}

module.exports = {
  extractJsonObject,
  generate,
  listModels,
};

