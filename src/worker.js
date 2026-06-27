const APP_VERSION = "petllama-worker-2026-06-27-chat-ui";

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
      width: min(720px, calc(100vw - 32px));
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

    textarea {
      min-height: 140px;
      resize: vertical;
      padding: 14px;
      border: 1px solid #c8ced8;
      border-radius: 8px;
      font: inherit;
      background: #ffffff;
      color: inherit;
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
      min-height: 120px;
      white-space: pre-wrap;
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
      <textarea id="message" name="message" placeholder="Ask something..." autocomplete="off" required></textarea>
      <button id="send" type="submit">Send</button>
    </form>
    <output id="response" aria-live="polite">petllama-worker-2026-06-27-chat-ui</output>
  </main>

  <script>
    const form = document.getElementById("chat-form");
    const message = document.getElementById("message");
    const response = document.getElementById("response");
    const send = document.getElementById("send");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const prompt = message.value.trim();
      if (!prompt) return;

      send.disabled = true;
      response.classList.remove("error");
      response.textContent = "Thinking...";

      try {
        const result = await fetch("/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: prompt })
        });

        const data = await result.json().catch(() => ({}));
        if (!result.ok) {
          throw new Error(data.error || "Request failed");
        }

        response.textContent = data.response || "";
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
  "cache-control": "no-store"
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return new Response(CHAT_PAGE, {
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "no-store"
        }
      });
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, version: APP_VERSION });
    }

    if (request.method === "POST" && url.pathname === "/chat") {
      return handleChat(request, env);
    }

    if (request.method === "OPTIONS" && url.pathname === "/chat") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    return json({ error: "Not found" }, 404);
  }
};

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

  const message = typeof body.message === "string" ? body.message.trim() : "";
  if (!message) {
    return json({ error: "message is required" }, 400);
  }

  const gatewayUrl = buildGatewayUrl(env.DAEDALUS_LLM_GATEWAY_URL, "/v1/summarise");
  const gatewayResponse = await fetch(gatewayUrl, {
    method: "POST",
    headers: {
      "authorization": `Bearer ${env.DAEDALUS_LLM_API_KEY}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      text: message,
      prompt: message,
      message,
      model: env.DAEDALUS_LLM_MODEL
    })
  });

  const gatewayText = await gatewayResponse.text();
  let gatewayJson = {};
  try {
    gatewayJson = gatewayText ? JSON.parse(gatewayText) : {};
  } catch {
    gatewayJson = { response: gatewayText };
  }

  if (!gatewayResponse.ok) {
    return json({
      error: gatewayJson.error || gatewayJson.message || "LLM gateway request failed"
    }, gatewayResponse.status);
  }

  return json({
    response: extractGatewayResponse(gatewayJson)
  });
}

function buildGatewayUrl(base, path) {
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const url = new URL(path.replace(/^\//, ""), normalizedBase);
  return url.toString();
}

function extractGatewayResponse(data) {
  if (typeof data === "string") return data;
  if (typeof data.summary === "string") return data.summary;
  if (typeof data.response === "string") return data.response;
  if (typeof data.output === "string") return data.output;
  if (typeof data.text === "string") return data.text;
  if (typeof data.result === "string") return data.result;
  return JSON.stringify(data, null, 2);
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      ...JSON_HEADERS,
      ...corsHeaders()
    }
  });
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type"
  };
}
