const APP_VERSION = "petllama-worker-2026-06-27-mode-bench";

const MODES = new Set([
  "chat",
  "summarise",
  "json",
  "extract-evidence",
  "self-test",
]);

const CHAT_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>petllama</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f4f5f7;
      color: #1f2933;
    }

    main {
      width: min(760px, calc(100vw - 32px));
      display: grid;
      gap: 16px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }

    form {
      display: grid;
      gap: 12px;
    }

    label {
      display: grid;
      gap: 6px;
      font-weight: 650;
    }

    select,
    textarea {
      width: 100%;
      box-sizing: border-box;
      padding: 12px 14px;
      border: 1px solid #c8ced8;
      border-radius: 8px;
      font: inherit;
      background: #ffffff;
      color: inherit;
    }

    textarea {
      min-height: 150px;
      resize: vertical;
    }

    button {
      justify-self: start;
      min-height: 42px;
      padding: 0 18px;
      border: 0;
      border-radius: 8px;
      background: #146c5c;
      color: #ffffff;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }

    output {
      min-height: 150px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 14px;
      border: 1px solid #d8dde6;
      border-radius: 8px;
      background: #ffffff;
    }

    .error {
      border-color: #c2410c;
      color: #9a3412;
    }

    @media (prefers-color-scheme: dark) {
      body {
        background: #121417;
        color: #edf2f7;
      }

      select,
      textarea,
      output {
        background: #1d2229;
        border-color: #384252;
      }

      button {
        background: #20a486;
      }

      .error {
        border-color: #f97316;
        color: #fdba74;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>petllama</h1>
    <form id="chat-form">
      <label>
        Mode
        <select id="mode" name="mode">
          <option value="chat">Chat</option>
          <option value="summarise">Summarise</option>
          <option value="json">JSON</option>
          <option value="extract-evidence">Extract evidence</option>
          <option value="self-test">Self-test</option>
        </select>
      </label>
      <label>
        Message
        <textarea id="message" name="message" placeholder="Ask something, paste text, or run self-test..."></textarea>
      </label>
      <button id="send" type="submit">Send</button>
    </form>
    <output id="response" aria-live="polite">petllama-worker-2026-06-27-mode-bench</output>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const mode = document.getElementById("mode");
    const message = document.getElementById("message");
    const response = document.getElementById("response");
    const send = document.getElementById("send");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const selectedMode = mode.value;
      const prompt = message.value.trim();

      if (selectedMode !== "self-test" && !prompt) {
        response.classList.add("error");
        response.textContent = "Enter a message for this mode.";
        return;
      }

      send.disabled = true;
      response.classList.remove("error");
      response.textContent = "Thinking...";

      try {
        const result = await fetch("/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ mode: selectedMode, message: prompt })
        });

        const data = await result.json().catch(() => ({}));
        if (!result.ok) {
          throw new Error(data.error || "Request failed");
        }

        response.textContent = data.response || JSON.stringify(data, null, 2);
      } catch (error) {
        response.classList.add("error");
        response.textContent = error.message || "Unable to reach the chat service.";
      } finally {
        send.disabled = false;
      }
    });
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
    return json({
      ok: true,
      version: APP_VERSION,
      config: {
        gatewayConfigured: Boolean(env.DAEDALUS_LLM_GATEWAY_URL),
        gatewayOrigin: safeOrigin(env.DAEDALUS_LLM_GATEWAY_URL),
        apiKeyConfigured: Boolean(env.DAEDALUS_LLM_API_KEY),
        modelConfigured: Boolean(env.DAEDALUS_LLM_MODEL),
        model: env.DAEDALUS_LLM_MODEL || null,
      },
    });
  }

  if (request.method === "POST" && url.pathname === "/chat") {
    return handleChat(request, env);
  }

  if (request.method === "OPTIONS" && url.pathname === "/chat") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  return json({ error: "Not found" }, 404);
}

async function handleChat(request, env) {
  if (!env.DAEDALUS_LLM_GATEWAY_URL || !env.DAEDALUS_LLM_API_KEY) {
    return json({ error: "LLM gateway is not configured" }, 500);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Expected JSON body" }, 400);
  }

  const mode = normalizeMode(body.mode);
  const message = typeof body.message === "string" ? body.message.trim() : "";

  if (mode !== "self-test" && !message) {
    return json({ error: "message is required" }, 400);
  }

  const gatewayResponse = await callGateway({ env, mode, message });
  const gatewayText = await gatewayResponse.text();
  const gatewayBody = parseGatewayBody(gatewayText);

  if (!gatewayResponse.ok) {
    return json({
      mode,
      error: gatewayBody.error || gatewayBody.message || "LLM gateway request failed",
      status: gatewayResponse.status,
    }, gatewayResponse.status);
  }

  return json({
    mode,
    endpoint: endpointForMode(mode),
    response: extractGatewayResponse(gatewayBody),
    raw: gatewayBody,
  });
}

function normalizeMode(mode) {
  const value = typeof mode === "string" ? mode : "chat";
  return MODES.has(value) ? value : "chat";
}

function callGateway({ env, mode, message }) {
  const endpoint = endpointForMode(mode);
  const method = mode === "self-test" ? "GET" : "POST";
  const init = {
    method,
    headers: gatewayHeaders(env),
  };

  if (method === "POST") {
    init.headers["content-type"] = "application/json";
    init.body = JSON.stringify(payloadForMode({ env, mode, message }));
  }

  return fetch(buildGatewayUrl(env.DAEDALUS_LLM_GATEWAY_URL, endpoint), init);
}

function gatewayHeaders(env) {
  return {
    "x-daedalus-api-key": env.DAEDALUS_LLM_API_KEY,
  };
}

function endpointForMode(mode) {
  if (mode === "json") return "/v1/json";
  if (mode === "extract-evidence") return "/v1/extract-evidence";
  if (mode === "self-test") return "/v1/self-test";
  return "/v1/summarise";
}

function payloadForMode({ env, mode, message }) {
  const model = env.DAEDALUS_LLM_MODEL || undefined;

  if (mode === "json") {
    return {
      model,
      prompt: message,
      schema: {
        answer: "string",
        key_points: ["string"],
        confidence: "low|medium|high",
      },
    };
  }

  if (mode === "extract-evidence") {
    return {
      model,
      question: "Extract the key claims and supporting evidence from this text.",
      text: message,
    };
  }

  if (mode === "chat") {
    return {
      model,
      text: message,
      maxWords: 220,
      instruction: [
        "Answer conversationally as a concise assistant.",
        "Use the text below as the user's message.",
        "Do not describe this as a summary unless the user asks for one.",
      ].join(" "),
    };
  }

  return {
    model,
    text: message,
    maxWords: 180,
  };
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
  if (data.json !== undefined) return JSON.stringify(data.json, null, 2);
  return JSON.stringify(data, null, 2);
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
