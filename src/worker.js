const APP_VERSION = "petllama-worker-2026-06-27-mobile-chat";

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
      min-height: 100dvh;
      background: #f4f5f7;
      color: #1f2933;
    }

    main {
      width: min(820px, 100vw);
      height: 100dvh;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      background: #f4f5f7;
    }

    h1 {
      margin: 0;
      padding: 18px 18px 12px;
      font-size: 26px;
      font-weight: 700;
      letter-spacing: 0;
    }

    .chat-history {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 10px 18px 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }

    .message {
      max-width: min(88%, 640px);
      padding: 12px 14px;
      border: 1px solid #d8dde6;
      border-radius: 8px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #ffffff;
    }

    .message.user {
      align-self: flex-end;
      background: #146c5c;
      border-color: #146c5c;
      color: #ffffff;
    }

    .message.bot {
      align-self: flex-start;
    }

    .message.error {
      border-color: #c2410c;
      color: #9a3412;
    }

    form {
      display: flex;
      align-items: end;
      gap: 12px;
      padding: 12px 18px calc(12px + env(safe-area-inset-bottom));
      border-top: 1px solid #d8dde6;
      background: #ffffff;
    }

    label {
      display: grid;
      gap: 6px;
      font-weight: 650;
    }

    .mode-field {
      width: 150px;
      flex: 0 0 150px;
    }

    .message-field {
      flex: 1;
      min-width: 0;
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
      min-height: 46px;
      max-height: 140px;
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

    @media (prefers-color-scheme: dark) {
      body {
        background: #121417;
        color: #edf2f7;
      }

      main {
        background: #121417;
      }

      form {
        background: #171b21;
        border-color: #384252;
      }

      select,
      textarea {
        background: #1d2229;
        border-color: #384252;
      }

      .message.bot {
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

    @media (max-width: 620px) {
      form {
        display: grid;
        grid-template-columns: 1fr auto;
      }

      .mode-field {
        grid-column: 1 / -1;
        width: 100%;
      }

      .message-field {
        min-width: 0;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>petllama</h1>
    <section id="chat-history" class="chat-history" aria-live="polite">
      <div class="message bot">petllama-worker-2026-06-27-mobile-chat</div>
    </section>
    <form id="chat-form">
      <label class="mode-field">
        Mode
        <select id="mode" name="mode">
          <option value="chat">Chat</option>
          <option value="summarise">Summarise</option>
          <option value="json">JSON</option>
          <option value="extract-evidence">Extract evidence</option>
          <option value="self-test">Self-test</option>
        </select>
      </label>
      <label class="message-field">
        Message
        <textarea id="message" name="message" placeholder="Type a message..." rows="1"></textarea>
      </label>
      <button id="send" type="submit">Send</button>
    </form>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const history = document.getElementById("chat-history");
    const mode = document.getElementById("mode");
    const message = document.getElementById("message");
    const send = document.getElementById("send");

    function appendMessage(kind, text) {
      const bubble = document.createElement("div");
      bubble.className = "message " + kind;
      bubble.textContent = text;
      history.appendChild(bubble);
      history.scrollTop = history.scrollHeight;
      return bubble;
    }

    message.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const selectedMode = mode.value;
      const prompt = message.value.trim();

      if (selectedMode !== "self-test" && !prompt) {
        appendMessage("error", "Enter a message for this mode.");
        return;
      }

      send.disabled = true;
      if (prompt) appendMessage("user", prompt);
      message.value = "";
      const pending = appendMessage("bot", "Thinking...");

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

        pending.textContent = data.response || JSON.stringify(data, null, 2);
      } catch (error) {
        pending.classList.add("error");
        pending.textContent = error.message || "Unable to reach the chat service.";
      } finally {
        send.disabled = false;
        message.focus();
        history.scrollTop = history.scrollHeight;
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
      maxWords: 120,
      system: "You are petllama, a direct conversational assistant. You are not summarising text unless explicitly asked.",
      instruction: [
        "Treat the text below as a chat message from the user.",
        "Reply naturally and directly.",
        "For greetings or small talk, respond like a normal assistant.",
        "Do not say there is no text to summarise.",
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
