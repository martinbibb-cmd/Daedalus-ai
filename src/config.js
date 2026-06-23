const DEFAULT_PORT = 8787;
const DEFAULT_HOST = '127.0.0.1';

function requireEnv(name, value) {
  if (!value || !String(value).trim()) {
    throw new Error(`${name} is required`);
  }
  return String(value).trim();
}

function loadConfig(env = process.env) {
  const ollamaBaseUrl = requireEnv('OLLAMA_BASE_URL', env.OLLAMA_BASE_URL).replace(/\/+$/, '');

  return {
    apiKey: requireEnv('DAEDALUS_LLM_API_KEY', env.DAEDALUS_LLM_API_KEY),
    ollamaBaseUrl,
    defaultModel: requireEnv('DEFAULT_MODEL', env.DEFAULT_MODEL),
    host: env.HOST || DEFAULT_HOST,
    port: Number.parseInt(env.PORT || String(DEFAULT_PORT), 10),
  };
}

module.exports = { loadConfig };

