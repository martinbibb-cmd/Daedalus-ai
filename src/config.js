const DEFAULT_PORT = 8787;
const DEFAULT_HOST = '127.0.0.1';

function requireEnv(name, value) {
  if (!value || !String(value).trim()) {
    throw new Error(`${name} is required`);
  }
  return String(value).trim();
}

function loadConfig(env = process.env) {
  const provider = String(env.LLM_PROVIDER || env.DAEDALUS_LLM_PROVIDER || 'ollama').trim().toLowerCase();
  const defaultModel = env.DEFAULT_MODEL || (provider === 'gemini' ? 'gemini-flash-latest' : '');
  const ollamaBaseUrl = provider === 'ollama'
    ? requireEnv('OLLAMA_BASE_URL', env.OLLAMA_BASE_URL).replace(/\/+$/, '')
    : String(env.OLLAMA_BASE_URL || '').replace(/\/+$/, '');

  return {
    apiKey: requireEnv('DAEDALUS_LLM_API_KEY', env.DAEDALUS_LLM_API_KEY),
    provider,
    ollamaBaseUrl,
    geminiApiKey: provider === 'gemini' ? requireEnv('GEMINI_API_KEY', env.GEMINI_API_KEY) : env.GEMINI_API_KEY,
    geminiBaseUrl: (env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com/v1beta').replace(/\/+$/, ''),
    defaultModel: requireEnv('DEFAULT_MODEL', defaultModel),
    host: env.HOST || DEFAULT_HOST,
    port: Number.parseInt(env.PORT || String(DEFAULT_PORT), 10),
    depotNotesExamplesDir: env.DEPOT_NOTES_EXAMPLES_DIR || '',
  };
}

module.exports = { loadConfig };

