const APP_VERSION = "petllama-v0.3-manual-ripper";
const DEFAULT_TIMEOUT_MS = 30000;

const MODES = new Set([
  "chat",
  "summarise",
  "extract-evidence",
  "json",
  "self-test",
  "manual-ripper",
]);

const CHAT_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pet Llama</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      background: #f3f5f7;
      color: #17202a;
    }

    main {
      width: min(1120px, 100vw);
      min-height: 100dvh;
      margin: 0 auto;
      display: grid;
      grid-template-rows: auto auto 1fr;
      background: #f3f5f7;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px;
      border-bottom: 1px solid #d8dde6;
      background: #ffffff;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 750;
      letter-spacing: 0;
    }

    .version {
      color: #627083;
      font-size: 13px;
    }

    .health {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      padding: 12px 18px;
      border-bottom: 1px solid #d8dde6;
      background: #ffffff;
    }

    .health-item,
    details,
    .panel,
    .control-bar {
      border: 1px solid #d8dde6;
      border-radius: 8px;
      background: #ffffff;
    }

    .health-item {
      padding: 10px;
      min-width: 0;
    }

    .health-label {
      display: block;
      color: #627083;
      font-size: 12px;
    }

    .health-value {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
    }

    .ok {
      color: #0f766e;
    }

    .bad {
      color: #b42318;
    }

    .workspace {
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 14px;
      padding: 14px 18px 18px;
    }

    .primary,
    .side {
      min-height: 0;
      display: grid;
      gap: 14px;
      align-content: start;
    }

    .control-bar {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
    }

    label {
      display: grid;
      gap: 6px;
      font-weight: 650;
    }

    select,
    textarea,
    input[type="range"] {
      width: 100%;
      box-sizing: border-box;
    }

    select,
    textarea {
      padding: 10px 12px;
      border: 1px solid #c8ced8;
      border-radius: 8px;
      font: inherit;
      background: #ffffff;
      color: inherit;
    }

    textarea {
      min-height: 190px;
      resize: vertical;
    }

    .schema-box {
      min-height: 110px;
    }

    .manual-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }

    .manual-file {
      padding: 10px 12px;
      border: 1px solid #c8ced8;
      border-radius: 8px;
      background: #ffffff;
      color: inherit;
    }

    .temp-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
    }

    .panel {
      padding: 14px;
    }

    .response {
      min-height: 220px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    button {
      min-height: 42px;
      padding: 0 18px;
      border: 0;
      border-radius: 8px;
      background: #146c5c;
      color: #ffffff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    button.secondary {
      background: #e8edf2;
      color: #17202a;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }

    details {
      padding: 0;
    }

    summary {
      cursor: pointer;
      padding: 12px 14px;
      font-weight: 750;
    }

    .details-body {
      display: grid;
      gap: 10px;
      padding: 0 14px 14px;
    }

    .kv {
      display: grid;
      grid-template-columns: 130px minmax(0, 1fr);
      gap: 8px;
      font-size: 13px;
    }

    .kv span:first-child {
      color: #627083;
    }

    pre {
      margin: 0;
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 12px;
      border-radius: 8px;
      background: #f0f3f6;
      font: 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    .trace {
      display: grid;
      gap: 8px;
    }

    .trace-step {
      display: grid;
      gap: 4px;
      padding: 10px;
      border: 1px solid #d8dde6;
      border-radius: 8px;
    }

    .trace-arrow {
      color: #627083;
      text-align: center;
    }

    .error-text {
      color: #b42318;
    }

    @media (prefers-color-scheme: dark) {
      body,
      main {
        background: #11161d;
        color: #edf2f7;
      }

      header,
      .health,
      .health-item,
      details,
      .panel,
      .control-bar,
      select,
      input[type="file"],
      textarea {
        background: #171d25;
        border-color: #344052;
      }

      button.secondary {
        background: #263241;
        color: #edf2f7;
      }

      pre {
        background: #10151b;
      }
    }

    @media (max-width: 860px) {
      main {
        grid-template-rows: auto auto auto;
      }

      header {
        align-items: start;
        flex-direction: column;
      }

      .health,
      .control-bar,
      .workspace {
        grid-template-columns: 1fr;
      }

      .workspace {
        padding: 12px;
      }

      textarea {
        min-height: 150px;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Pet Llama v0.2</h1>
        <div class="version">AI Gateway Engineering Console</div>
      </div>
      <button id="refresh-health" class="secondary" type="button">Refresh health</button>
    </header>

    <section class="health" aria-live="polite">
      <div class="health-item"><span class="health-label">Gateway</span><span id="health-gateway" class="health-value">Checking...</span></div>
      <div class="health-item"><span class="health-label">Tunnel</span><span id="health-tunnel" class="health-value">Checking...</span></div>
      <div class="health-item"><span class="health-label">LLM</span><span id="health-llm" class="health-value">Checking...</span></div>
      <div class="health-item"><span class="health-label">Model</span><span id="health-model" class="health-value">-</span></div>
      <div class="health-item"><span class="health-label">Worker</span><span id="health-worker" class="health-value">${APP_VERSION}</span></div>
    </section>

    <section class="workspace">
      <div class="primary">
        <section class="control-bar">
          <label>
            Mode
            <select id="mode">
              <option value="chat">Chat</option>
              <option value="summarise">Summarise</option>
              <option value="extract-evidence">Extract Evidence</option>
              <option value="json">JSON</option>
              <option value="self-test">Self Test</option>
              <option value="manual-ripper">Manual Ripper</option>
            </select>
          </label>
          <label>
            Model
            <select id="model">
              <option value="">Loading models...</option>
            </select>
          </label>
          <label>
            Temperature
            <span class="temp-row">
              <input id="temperature" type="range" min="0" max="1.5" step="0.1" value="0.4">
              <strong id="temperature-value">0.4</strong>
            </span>
          </label>
          <div class="actions">
            <button id="send" type="button">Send</button>
            <button id="clear" class="secondary" type="button">Clear</button>
          </div>
        </section>

        <label class="panel">
          Prompt
          <textarea id="prompt" placeholder="Enter prompt, source text, or diagnostic input..."></textarea>
        </label>

        <label id="schema-panel" class="panel" hidden>
          Optional JSON schema
          <textarea id="schema" class="schema-box" placeholder='{"answer":"string","confidence":"low|medium|high"}'></textarea>
        </label>

        <section id="manual-panel" class="panel" hidden>
          <strong>Manual Ripper</strong>
          <div class="manual-grid">
            <label>
              PDF upload
              <input id="manual-file" class="manual-file" type="file" accept="application/pdf,.pdf">
            </label>
            <button id="manual-upload" type="button">Upload</button>
          </div>
          <label>
            Manual library
            <select id="manual-list">
              <option value="">No manuals loaded</option>
            </select>
          </label>
          <button id="manual-refresh" class="secondary" type="button">Refresh manuals</button>
        </section>

        <section class="panel">
          <strong>Response</strong>
          <div id="response" class="response">Ready.</div>
        </section>
      </div>

      <aside class="side">
        <details open>
          <summary>Diagnostics</summary>
          <div class="details-body">
            <div class="kv"><span>Worker version</span><strong id="diag-worker">${APP_VERSION}</strong></div>
            <div class="kv"><span>Gateway URL</span><strong id="diag-gateway">-</strong></div>
            <div class="kv"><span>Selected model</span><strong id="diag-model">-</strong></div>
            <div class="kv"><span>Mode</span><strong id="diag-mode">-</strong></div>
            <div class="kv"><span>HTTP status</span><strong id="diag-status">-</strong></div>
            <div class="kv"><span>Total request time</span><strong id="diag-total">-</strong></div>
            <div class="kv"><span>Gateway time</span><strong id="diag-gateway-time">-</strong></div>
          </div>
        </details>

        <details>
          <summary>Trace</summary>
          <div id="trace" class="details-body trace"></div>
        </details>

        <details>
          <summary>Advanced</summary>
          <div class="details-body">
            <strong>Raw request JSON</strong>
            <pre id="raw-request">{}</pre>
            <strong>Raw response JSON</strong>
            <pre id="raw-response">{}</pre>
          </div>
        </details>
      </aside>
    </section>
  </main>

  <script>
    const state = {
      workerVersion: "${APP_VERSION}",
      gatewayOrigin: "-",
      defaultModel: "",
      lastHealth: null
    };

    const els = {
      mode: document.getElementById("mode"),
      model: document.getElementById("model"),
      temperature: document.getElementById("temperature"),
      temperatureValue: document.getElementById("temperature-value"),
      prompt: document.getElementById("prompt"),
      schemaPanel: document.getElementById("schema-panel"),
      schema: document.getElementById("schema"),
      manualPanel: document.getElementById("manual-panel"),
      manualFile: document.getElementById("manual-file"),
      manualUpload: document.getElementById("manual-upload"),
      manualList: document.getElementById("manual-list"),
      manualRefresh: document.getElementById("manual-refresh"),
      send: document.getElementById("send"),
      clear: document.getElementById("clear"),
      response: document.getElementById("response"),
      trace: document.getElementById("trace"),
      rawRequest: document.getElementById("raw-request"),
      rawResponse: document.getElementById("raw-response"),
      diagGateway: document.getElementById("diag-gateway"),
      diagModel: document.getElementById("diag-model"),
      diagMode: document.getElementById("diag-mode"),
      diagStatus: document.getElementById("diag-status"),
      diagTotal: document.getElementById("diag-total"),
      diagGatewayTime: document.getElementById("diag-gateway-time"),
      healthGateway: document.getElementById("health-gateway"),
      healthTunnel: document.getElementById("health-tunnel"),
      healthLlm: document.getElementById("health-llm"),
      healthModel: document.getElementById("health-model"),
      healthWorker: document.getElementById("health-worker"),
      refreshHealth: document.getElementById("refresh-health")
    };

    function setHealth(el, ok, text) {
      el.className = "health-value " + (ok ? "ok" : "bad");
      el.textContent = text;
    }

    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    function safeText(value) {
      if (value === undefined || value === null || value === "") return "-";
      return String(value);
    }

    function renderTrace(data) {
      const trace = data && data.trace ? data.trace : [];
      els.trace.textContent = "";
      for (let i = 0; i < trace.length; i += 1) {
        const step = trace[i];
        const node = document.createElement("div");
        node.className = "trace-step";
        const meta = [
          step.endpoint ? "endpoint: " + step.endpoint : "",
          step.model ? "model: " + step.model : "",
          step.status ? "status: " + step.status : "",
          step.latencyMs !== undefined ? "latency: " + step.latencyMs + "ms" : ""
        ].filter(Boolean).join(" | ");
        node.textContent = step.name + (meta ? "\\n" + meta : "");
        els.trace.appendChild(node);
        if (i < trace.length - 1) {
          const arrow = document.createElement("div");
          arrow.className = "trace-arrow";
          arrow.textContent = "↓";
          els.trace.appendChild(arrow);
        }
      }
    }

    function updateDiagnostics(data) {
      const diagnostics = data.diagnostics || {};
      els.diagGateway.textContent = safeText(diagnostics.gatewayUrl || state.gatewayOrigin);
      els.diagModel.textContent = safeText(diagnostics.selectedModel || els.model.value);
      els.diagMode.textContent = safeText(diagnostics.mode || els.mode.value);
      els.diagStatus.textContent = safeText(diagnostics.httpStatus);
      els.diagTotal.textContent = diagnostics.totalMs !== undefined ? diagnostics.totalMs + "ms" : "-";
      els.diagGatewayTime.textContent = diagnostics.gatewayMs !== undefined ? diagnostics.gatewayMs + "ms" : "-";
    }

    function responseText(data) {
      if (data.response !== undefined) {
        return typeof data.response === "string" ? data.response : pretty(data.response);
      }
      if (data.error) return data.error;
      return pretty(data);
    }

    async function loadModels() {
      try {
        const result = await fetch("/models", { cache: "no-store" });
        const data = await result.json();
        if (!result.ok) throw new Error(data.error || "Unable to load models");
        const models = Array.isArray(data.models) ? data.models : [];
        state.defaultModel = data.defaultModel || data.configuredModel || "";
        els.model.textContent = "";
        for (const item of models) {
          const name = typeof item === "string" ? item : item.name;
          if (!name) continue;
          const option = document.createElement("option");
          option.value = name;
          option.textContent = name;
          els.model.appendChild(option);
        }
        if (!models.length && state.defaultModel) {
          const option = document.createElement("option");
          option.value = state.defaultModel;
          option.textContent = state.defaultModel;
          els.model.appendChild(option);
        }
        if (state.defaultModel) els.model.value = state.defaultModel;
      } catch (error) {
        els.model.textContent = "";
        const option = document.createElement("option");
        option.value = state.defaultModel;
        option.textContent = state.defaultModel || "Model unavailable";
        els.model.appendChild(option);
      }
    }

    async function refreshHealth() {
      try {
        const result = await fetch("/health", { cache: "no-store" });
        const data = await result.json();
        state.lastHealth = data;
        state.gatewayOrigin = data.config && data.config.gatewayOrigin ? data.config.gatewayOrigin : "-";
        state.defaultModel = data.config && data.config.model ? data.config.model : state.defaultModel;
        setHealth(els.healthGateway, Boolean(data.gateway && data.gateway.ok), data.gateway && data.gateway.ok ? "✅ " + data.gateway.status : "❌ " + safeText(data.gateway && data.gateway.status));
        setHealth(els.healthTunnel, Boolean(data.tunnel && data.tunnel.ok), data.tunnel && data.tunnel.ok ? "✅ reachable" : "❌ unavailable");
        setHealth(els.healthLlm, Boolean(data.llm && data.llm.ok), data.llm && data.llm.ok ? "✅ " + safeText(data.llm.model || state.defaultModel) : "❌ " + safeText(data.llm && data.llm.status));
        els.healthModel.textContent = safeText(state.defaultModel);
        els.healthWorker.textContent = data.version || state.workerVersion;
        els.diagGateway.textContent = state.gatewayOrigin;
      } catch (error) {
        setHealth(els.healthGateway, false, "❌ unreachable");
        setHealth(els.healthTunnel, false, "❌ unavailable");
        setHealth(els.healthLlm, false, "❌ unknown");
      }
    }

    async function loadManuals() {
      try {
        const result = await fetch("/manuals", { cache: "no-store" });
        const data = await result.json();
        if (!result.ok) throw new Error(data.error || "Manual Ripper service is unreachable");
        const manuals = Array.isArray(data.manuals) ? data.manuals : [];
        els.manualList.textContent = "";
        if (!manuals.length) {
          const option = document.createElement("option");
          option.value = "";
          option.textContent = "No manuals loaded";
          els.manualList.appendChild(option);
          return;
        }
        for (const manual of manuals) {
          const option = document.createElement("option");
          option.value = manual.id;
          option.textContent = [manual.manufacturer, manual.model].filter(Boolean).join(" ") || manual.filename;
          els.manualList.appendChild(option);
        }
      } catch (error) {
        els.manualList.textContent = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Manual Ripper unreachable";
        els.manualList.appendChild(option);
      }
    }

    async function uploadManual() {
      const file = els.manualFile.files && els.manualFile.files[0];
      if (!file) {
        els.response.classList.add("error-text");
        els.response.textContent = "Choose a PDF manual first.";
        return;
      }
      const formData = new FormData();
      formData.append("file", file);
      els.manualUpload.disabled = true;
      els.response.classList.remove("error-text");
      els.response.textContent = "Uploading manual...";
      try {
        const result = await fetch("/manuals/upload", { method: "POST", body: formData });
        const data = await result.json().catch(() => ({}));
        els.rawResponse.textContent = pretty(data);
        if (!result.ok) throw new Error(data.error || data.detail || "Manual upload failed");
        els.response.textContent = "Uploaded manual. Extracting text...";
        await fetch("/manuals/" + encodeURIComponent(data.manual.id) + "/extract", { method: "POST" });
        await loadManuals();
        els.manualList.value = data.manual.id;
        els.response.textContent = "Manual uploaded and extraction requested.";
      } catch (error) {
        els.response.classList.add("error-text");
        els.response.textContent = error.message || "Manual Ripper service is unreachable.";
      } finally {
        els.manualUpload.disabled = false;
      }
    }

    async function sendRequest() {
      if (els.mode.value === "manual-ripper") {
        return sendManualQuestion();
      }

      const schemaText = els.schema.value.trim();
      let schema = null;
      if (els.mode.value === "json" && schemaText) {
        try {
          schema = JSON.parse(schemaText);
        } catch (error) {
          els.response.classList.add("error-text");
          els.response.textContent = "Invalid JSON schema: " + error.message;
          return;
        }
      }

      const request = {
        mode: els.mode.value,
        message: els.prompt.value.trim(),
        model: els.model.value,
        temperature: Number(els.temperature.value),
        schema
      };

      if (request.mode !== "self-test" && !request.message) {
        els.response.classList.add("error-text");
        els.response.textContent = "Prompt is required for this mode.";
        return;
      }

      els.send.disabled = true;
      els.response.classList.remove("error-text");
      els.response.textContent = "Running...";
      els.rawRequest.textContent = pretty(request);

      try {
        const result = await fetch("/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(request)
        });
        const data = await result.json().catch(() => ({}));
        els.rawResponse.textContent = pretty(data);
        updateDiagnostics(data);
        renderTrace(data);
        if (!result.ok) {
          els.response.classList.add("error-text");
        }
        els.response.textContent = responseText(data);
      } catch (error) {
        const data = { error: "Worker request failed", detail: error.message };
        els.rawResponse.textContent = pretty(data);
        els.response.classList.add("error-text");
        els.response.textContent = data.error + ": " + data.detail;
      } finally {
        els.send.disabled = false;
      }
    }

    async function sendManualQuestion() {
      const manualId = els.manualList.value;
      const question = els.prompt.value.trim();
      if (!manualId) {
        els.response.classList.add("error-text");
        els.response.textContent = "Select or upload a manual first.";
        return;
      }
      if (!question) {
        els.response.classList.add("error-text");
        els.response.textContent = "Question is required for Manual Ripper.";
        return;
      }
      const request = { question, limit: 5 };
      els.send.disabled = true;
      els.response.classList.remove("error-text");
      els.response.textContent = "Querying manual evidence...";
      els.rawRequest.textContent = pretty({ manual_id: manualId, ...request });
      try {
        const result = await fetch("/manuals/" + encodeURIComponent(manualId) + "/query", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(request)
        });
        const data = await result.json().catch(() => ({}));
        els.rawResponse.textContent = pretty(data);
        if (!result.ok) throw new Error(data.error || data.detail || "Manual query failed");
        const evidence = Array.isArray(data.evidence) ? data.evidence : [];
        els.response.textContent = [
          data.answer || "No answer returned.",
          "",
          "Evidence:",
          ...evidence.map((item) => "Page " + item.page + " [" + item.confidence + "]: " + item.snippet)
        ].join("\\n");
        updateDiagnostics({
          diagnostics: {
            gatewayUrl: "Manual Ripper",
            selectedModel: els.model.value,
            mode: "manual-ripper",
            httpStatus: result.status
          }
        });
      } catch (error) {
        els.response.classList.add("error-text");
        els.response.textContent = error.message || "Manual Ripper service is unreachable.";
      } finally {
        els.send.disabled = false;
      }
    }

    els.temperature.addEventListener("input", () => {
      els.temperatureValue.textContent = els.temperature.value;
    });

    els.mode.addEventListener("change", () => {
      els.schemaPanel.hidden = els.mode.value !== "json";
      els.manualPanel.hidden = els.mode.value !== "manual-ripper";
      els.diagMode.textContent = els.mode.value;
      if (els.mode.value === "manual-ripper") loadManuals();
    });

    els.model.addEventListener("change", () => {
      els.diagModel.textContent = els.model.value;
    });

    els.send.addEventListener("click", sendRequest);
    els.manualUpload.addEventListener("click", uploadManual);
    els.manualRefresh.addEventListener("click", loadManuals);
    els.clear.addEventListener("click", () => {
      els.prompt.value = "";
      els.response.textContent = "Ready.";
      els.trace.textContent = "";
      els.rawRequest.textContent = "{}";
      els.rawResponse.textContent = "{}";
    });
    els.refreshHealth.addEventListener("click", refreshHealth);

    loadModels().then(refreshHealth).then(loadManuals);
    setInterval(refreshHealth, 30000);
  </script>
</body>
</html>`;

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request, globalThis));
});

async function handleRequest(request, env) {
  const url = new URL(request.url);

  if (request.method === "GET" && url.pathname === "/") {
    return new Response(CHAT_PAGE, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "no-store",
      },
    });
  }

  if (request.method === "GET" && url.pathname === "/health") {
    return handleHealth(env);
  }

  if (request.method === "GET" && url.pathname === "/models") {
    return handleModels(env);
  }

  if (url.pathname === "/manuals" || url.pathname.startsWith("/manuals/")) {
    return handleManualProxy(request, env, url);
  }

  if (request.method === "POST" && url.pathname === "/chat") {
    return handleChat(request, env);
  }

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  return json({ error: "Not found" }, 404);
}

async function handleManualProxy(request, env, url) {
  if (!env.MANUAL_RIPPER_BASE_URL) {
    return json({
      error: "Manual Ripper service is not configured",
      detail: "Set MANUAL_RIPPER_BASE_URL to the private service URL or Cloudflare Tunnel route.",
    }, 503);
  }

  const started = Date.now();
  const target = buildGatewayUrl(env.MANUAL_RIPPER_BASE_URL, url.pathname);
  const headers = {};
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    });
    const text = await upstream.text();
    const body = parseGatewayBody(text);
    return json({
      ...safeGatewayBody(body),
      diagnostics: {
        service: "manual-ripper",
        endpoint: url.pathname,
        httpStatus: upstream.status,
        totalMs: Date.now() - started,
      },
    }, upstream.status);
  } catch (error) {
    return json({
      error: "Manual Ripper service is unreachable",
      detail: error && error.message ? error.message : String(error),
      diagnostics: {
        service: "manual-ripper",
        endpoint: url.pathname,
        httpStatus: 0,
        totalMs: Date.now() - started,
      },
    }, 502);
  }
}

async function handleModels(env) {
  const configuredModel = env.DAEDALUS_LLM_MODEL || null;
  if (!hasGatewayConfig(env)) {
    return json({
      error: "LLM gateway is not configured",
      defaultModel: configuredModel,
      models: configuredModel ? [{ name: configuredModel }] : [],
    }, 500);
  }

  const result = await gatewayFetch(env, "/models", { method: "GET", auth: true });
  if (!result.ok) {
    return json({
      error: classifyGatewayError(result),
      status: result.status,
      defaultModel: configuredModel,
      models: configuredModel ? [{ name: configuredModel }] : [],
      body: safeGatewayBody(result.body),
    }, result.status || 502);
  }

  return json({
    defaultModel: result.body.defaultModel || configuredModel,
    configuredModel,
    models: Array.isArray(result.body.models) ? result.body.models : [],
  });
}

async function handleHealth(env) {
  const gatewayOrigin = safeOrigin(env.DAEDALUS_LLM_GATEWAY_URL);
  const configuredModel = env.DAEDALUS_LLM_MODEL || null;
  const health = await gatewayFetch(env, "/health", { method: "GET", auth: false, timeoutMs: 8000 });
  const models = hasGatewayConfig(env)
    ? await gatewayFetch(env, "/models", { method: "GET", auth: true, timeoutMs: 10000 })
    : null;
  const selfTest = hasGatewayConfig(env)
    ? await gatewayFetch(env, "/v1/self-test", { method: "GET", auth: true, timeoutMs: 20000 })
    : null;

  return json({
    ok: Boolean(health.ok && (!selfTest || selfTest.ok)),
    version: APP_VERSION,
    config: {
      gatewayConfigured: Boolean(env.DAEDALUS_LLM_GATEWAY_URL),
      gatewayOrigin,
      apiKeyConfigured: Boolean(env.DAEDALUS_LLM_API_KEY),
      modelConfigured: Boolean(env.DAEDALUS_LLM_MODEL),
      model: configuredModel,
    },
    gateway: diagnosticFromResult(health),
    tunnel: {
      ok: Boolean(health.ok || (health.status && health.status !== 0)),
      status: health.status || 0,
      latencyMs: health.ms,
    },
    llm: selfTest ? {
      ok: Boolean(selfTest.ok),
      status: selfTest.status,
      latencyMs: selfTest.ms,
      model: selfTest.body.model || configuredModel,
      error: selfTest.ok ? undefined : classifyGatewayError(selfTest),
    } : {
      ok: false,
      status: 0,
      model: configuredModel,
      error: "LLM gateway is not configured",
    },
    models: models && models.ok && Array.isArray(models.body.models) ? models.body.models : [],
  });
}

async function handleChat(request, env) {
  const workerStarted = Date.now();
  if (!hasGatewayConfig(env)) {
    return json({ error: "LLM gateway is not configured" }, 500);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON", detail: "Expected JSON body" }, 400);
  }

  const mode = normalizeMode(body.mode);
  const message = typeof body.message === "string" ? body.message.trim() : "";
  const model = typeof body.model === "string" && body.model ? body.model : env.DAEDALUS_LLM_MODEL;
  const temperature = normalizeTemperature(body.temperature);
  const schema = body.schema && typeof body.schema === "object" ? body.schema : undefined;

  if (mode !== "self-test" && !message) {
    return json({ error: "Prompt is required for this mode" }, 400);
  }

  const requestBody = payloadForMode({ mode, message, model, temperature, schema });
  const initialEndpoint = endpointForMode(mode);
  let endpoint = initialEndpoint;
  let gateway = await gatewayFetch(env, endpoint, {
    method: mode === "self-test" ? "GET" : "POST",
    auth: true,
    body: mode === "self-test" ? undefined : requestBody,
  });

  let fallbackUsed = false;
  if (mode === "chat" && (gateway.status === 404 || gateway.status === 405)) {
    fallbackUsed = true;
    endpoint = "/v1/summarise";
    gateway = await gatewayFetch(env, endpoint, {
      method: "POST",
      auth: true,
      body: chatFallbackPayload({ message, model, temperature }),
    });
  }

  const totalMs = Date.now() - workerStarted;
  const responseStatus = gateway.ok ? 200 : gateway.status || 502;
  const responsePayload = {
    mode,
    endpoint,
    fallbackUsed,
    response: gateway.ok ? extractGatewayResponse(gateway.body) : undefined,
    error: gateway.ok ? undefined : classifyGatewayError(gateway),
    safeBody: gateway.ok ? undefined : safeGatewayBody(gateway.body),
    diagnostics: {
      workerVersion: APP_VERSION,
      gatewayUrl: safeOrigin(env.DAEDALUS_LLM_GATEWAY_URL),
      selectedModel: model,
      mode,
      httpStatus: gateway.status,
      totalMs,
      gatewayMs: gateway.ms,
    },
    trace: buildTrace({
      prompt: message,
      endpoint,
      model,
      status: gateway.status,
      gatewayMs: gateway.ms,
      totalMs,
    }),
    rawRequest: {
      endpoint,
      mode,
      model,
      temperature,
      body: requestBody,
    },
    rawResponse: gateway.body,
  };

  return json(responsePayload, responseStatus);
}

function hasGatewayConfig(env) {
  return Boolean(env.DAEDALUS_LLM_GATEWAY_URL && env.DAEDALUS_LLM_API_KEY);
}

async function gatewayFetch(env, endpoint, options = {}) {
  const started = Date.now();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || DEFAULT_TIMEOUT_MS);
  const headers = {};

  if (options.auth) {
    headers["x-daedalus-api-key"] = env.DAEDALUS_LLM_API_KEY;
  }

  if (options.body !== undefined) {
    headers["content-type"] = "application/json";
  }

  try {
    const response = await fetch(buildGatewayUrl(env.DAEDALUS_LLM_GATEWAY_URL, endpoint), {
      method: options.method || "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    });
    const text = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      ms: Date.now() - started,
      body: parseGatewayBody(text),
    };
  } catch (error) {
    return {
      ok: false,
      status: error && error.name === "AbortError" ? 504 : 0,
      ms: Date.now() - started,
      body: {
        error: error && error.name === "AbortError" ? "Timeout" : "Gateway unreachable",
        detail: error && error.message ? error.message : String(error),
      },
    };
  } finally {
    clearTimeout(timeout);
  }
}

function diagnosticFromResult(result) {
  return {
    ok: Boolean(result.ok),
    status: result.status,
    latencyMs: result.ms,
    error: result.ok ? undefined : classifyGatewayError(result),
  };
}

function classifyGatewayError(result) {
  if (result.status === 0) return "Gateway unreachable";
  if (result.status === 401 || result.status === 403) return "Authentication failed";
  if (result.status === 404) return "Endpoint or model unavailable";
  if (result.status === 408 || result.status === 504) return "Timeout";
  if (result.body && result.body.error) return String(result.body.error);
  return `Gateway request failed with HTTP ${result.status}`;
}

function safeGatewayBody(body) {
  if (!body || typeof body !== "object") return body;
  const clone = JSON.parse(JSON.stringify(body));
  redactObject(clone);
  return clone;
}

function redactObject(value) {
  if (!value || typeof value !== "object") return;
  for (const key of Object.keys(value)) {
    if (/key|token|secret|authorization/i.test(key)) {
      value[key] = "[redacted]";
    } else {
      redactObject(value[key]);
    }
  }
}

function normalizeMode(mode) {
  const value = typeof mode === "string" ? mode : "chat";
  return MODES.has(value) ? value : "chat";
}

function normalizeTemperature(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0.4;
  return Math.min(1.5, Math.max(0, number));
}

function endpointForMode(mode) {
  if (mode === "chat") return "/v1/chat";
  if (mode === "summarise") return "/v1/summarise";
  if (mode === "extract-evidence") return "/v1/extract-evidence";
  if (mode === "json") return "/v1/json";
  if (mode === "self-test") return "/v1/self-test";
  return "/v1/summarise";
}

function payloadForMode({ mode, message, model, temperature, schema }) {
  if (mode === "chat") {
    return {
      model,
      message,
      temperature,
      system: "You are petllama, a direct conversational assistant for gateway testing.",
    };
  }

  if (mode === "summarise") {
    return {
      model,
      text: message,
      maxWords: 180,
      temperature,
    };
  }

  if (mode === "extract-evidence") {
    return {
      model,
      question: "Extract the key claims and supporting evidence from this text.",
      text: message,
      temperature,
    };
  }

  if (mode === "json") {
    return {
      model,
      prompt: message,
      schema: schema || {
        answer: "string",
        key_points: ["string"],
        confidence: "low|medium|high",
      },
      temperature,
    };
  }

  return undefined;
}

function chatFallbackPayload({ message, model, temperature }) {
  return {
    model,
    text: message,
    maxWords: 140,
    temperature,
    system: "You are petllama, a direct conversational assistant. You are not summarising text unless explicitly asked.",
    instruction: [
      "Treat the text below as a chat message from the user.",
      "Reply naturally and directly.",
      "Do not say there is no text to summarise.",
    ].join(" "),
  };
}

function buildTrace({ prompt, endpoint, model, status, gatewayMs, totalMs }) {
  return [
    { name: "Prompt", latencyMs: 0 },
    { name: "Worker", endpoint: "/chat", model, latencyMs: totalMs, status },
    { name: "Tunnel", endpoint: safePath(endpoint), latencyMs: gatewayMs, status },
    { name: "Gateway", endpoint, model, latencyMs: gatewayMs, status },
    { name: "Model", model, latencyMs: gatewayMs, status },
    { name: "Response", latencyMs: totalMs, status },
  ].map((step, index) => index === 0 ? { ...step, promptLength: prompt.length } : step);
}

function safePath(endpoint) {
  return endpoint || "-";
}

function buildGatewayUrl(base, path) {
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const url = new URL(path.replace(/^\//, ""), normalizedBase);
  return url.toString();
}

function parseGatewayBody(text) {
  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    return { response: text };
  }
}

function extractGatewayResponse(data) {
  if (typeof data === "string") return data;
  if (typeof data.summary === "string") return data.summary;
  if (typeof data.sample === "string") return data.sample;
  if (typeof data.response === "string") return data.response;
  if (typeof data.output === "string") return data.output;
  if (typeof data.text === "string") return data.text;
  if (typeof data.result === "string") return data.result;
  if (data.json !== undefined) return data.json;
  return data;
}

function safeOrigin(value) {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return "invalid-url";
  }
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...JSON_HEADERS,
      ...corsHeaders(),
    },
  });
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type",
  };
}
