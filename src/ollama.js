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
  const response = await fetchImpl(`${config.ollamaBaseUrl}/api/tags`);
  const body = await readJsonResponse(response);

  return {
    defaultModel: config.defaultModel,
    models: Array.isArray(body.models) ? body.models : [],
  };
}

async function generate({ config, fetchImpl = fetch, model, prompt, system, format, options }) {
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

module.exports = {
  extractJsonObject,
  generate,
  listModels,
};

