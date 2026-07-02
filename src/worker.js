const APP_VERSION = "hitchhikers-guide-to-boilers-v0.5";
const DEFAULT_TIMEOUT_MS = 30000;

const MODES = new Set([
  "chat",
  "summarise",
  "extract-evidence",
  "json",
  "self-test",
  "manual-ripper",
]);

const WELCOME_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Hitchhiker's Guide to Boilers</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      display: grid;
      place-items: center;
      background: #f6f1df;
      color: #1f2933;
    }

    main {
      width: min(760px, calc(100vw - 32px));
      display: grid;
      gap: 28px;
      text-align: center;
    }

    h1 {
      margin: 0;
      font-size: clamp(38px, 9vw, 82px);
      line-height: 0.95;
      letter-spacing: 0;
    }

    .panic {
      margin: 0;
      color: #0f766e;
      font-size: clamp(42px, 12vw, 110px);
      font-weight: 900;
      letter-spacing: 0;
    }

    .links {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 12px;
    }

    a {
      justify-self: center;
      min-width: 132px;
      padding: 14px 24px;
      border-radius: 8px;
      background: #17202a;
      color: #ffffff;
      text-decoration: none;
      font-weight: 800;
    }

    @media (prefers-color-scheme: dark) {
      body {
        background: #141813;
        color: #f4f1df;
      }

      a {
        background: #f4f1df;
        color: #141813;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>The Hitchhiker's Guide to Boilers</h1>
    <p class="panic">DON'T PANIC</p>
    <div class="links">
      <a href="/chat">Enter</a>
      <a href="/depot-notes">Depot Notes</a>
    </div>
  </main>
</body>
</html>`;

const PUBLIC_CHAT_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Boiler Guide Chat</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      background: #eef3f1;
      color: #17202a;
    }

    main {
      min-height: 100dvh;
      display: grid;
      grid-template-rows: auto 1fr auto;
    }

    header {
      padding: 16px max(16px, calc((100vw - 920px) / 2));
      background: #ffffff;
      border-bottom: 1px solid #d7dedb;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }

    .messages {
      min-height: 0;
      overflow: auto;
      display: grid;
      align-content: start;
      gap: 14px;
      padding: 18px max(16px, calc((100vw - 920px) / 2)) 120px;
    }

    .message {
      max-width: min(760px, 92vw);
      display: grid;
      gap: 10px;
      padding: 14px;
      border: 1px solid #d7dedb;
      border-radius: 8px;
      background: #ffffff;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    .message.user {
      justify-self: end;
      background: #dff3ee;
      border-color: #9bd5c9;
    }

    .message.assistant {
      justify-self: start;
    }

    .meta,
    .citations {
      color: #627083;
      font-size: 13px;
    }

    .citations,
    .evidence {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .citations a {
      color: #146c5c;
      font-weight: 750;
    }

    .evidence-card {
      width: 150px;
      display: grid;
      gap: 6px;
      padding: 8px;
      border: 1px solid #d7dedb;
      border-radius: 8px;
      background: #f8faf9;
      color: inherit;
      text-decoration: none;
      font-size: 12px;
    }

    .evidence-card img {
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: contain;
      border: 1px solid #d7dedb;
      border-radius: 6px;
      background: #ffffff;
    }

    form {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      padding: 14px max(16px, calc((100vw - 920px) / 2));
      background: rgba(255, 255, 255, 0.96);
      border-top: 1px solid #d7dedb;
    }

    textarea {
      min-height: 48px;
      max-height: 140px;
      resize: vertical;
      padding: 12px;
      border: 1px solid #b9c5c0;
      border-radius: 8px;
      font: inherit;
      background: #ffffff;
      color: inherit;
    }

    button {
      min-height: 48px;
      padding: 0 20px;
      border: 0;
      border-radius: 8px;
      background: #146c5c;
      color: #ffffff;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }

    @media (prefers-color-scheme: dark) {
      body {
        background: #10151b;
        color: #edf2f7;
      }

      header,
      .message,
      form,
      textarea {
        background: #171d25;
        border-color: #344052;
      }

      .message.user {
        background: #123b35;
        border-color: #1c665b;
      }

      .evidence-card {
        background: #10151b;
        border-color: #344052;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>The Hitchhiker's Guide to Boilers</h1>
    </header>
    <section id="messages" class="messages" aria-live="polite"></section>
    <form id="chat-form">
      <textarea id="question" placeholder="Ask about any stored manual, document, or regulation..."></textarea>
      <button id="send" type="submit">Send</button>
    </form>
  </main>
  <script>
    const state = {
      history: JSON.parse(sessionStorage.getItem("boilerGuideHistory") || "[]"),
      context: JSON.parse(sessionStorage.getItem("boilerGuideContext") || "{}")
    };
    const messages = document.getElementById("messages");
    const form = document.getElementById("chat-form");
    const question = document.getElementById("question");
    const send = document.getElementById("send");

    function saveHistory() {
      sessionStorage.setItem("boilerGuideHistory", JSON.stringify(state.history.slice(-40)));
      sessionStorage.setItem("boilerGuideContext", JSON.stringify(state.context || {}));
    }

    function queryTerms(text) {
      return String(text || "").toLowerCase().match(/[a-z0-9]{3,}/g) || [];
    }

    function isAmbiguousFollowUp(text) {
      const terms = queryTerms(text).filter((term) => !["how", "about", "what", "the", "and", "for", "with", "that", "this"].includes(term));
      return terms.length <= 3 && Boolean(state.context && state.context.current_manual_id);
    }

    function rewriteQuestion(text) {
      if (!isAmbiguousFollowUp(text)) return text;
      const terms = queryTerms(text);
      const focus = terms.includes("weight")
        ? "appliance weight lift weight"
        : terms.includes("height")
          ? "appliance height dimensions"
          : text;
      return [
        state.context.current_manual_name || "",
        state.context.current_subject || "",
        focus
      ].filter(Boolean).join(" ");
    }

    function usefulResult(payload) {
      if (!payload || payload.error) return false;
      const answer = String(payload.answer || "").toLowerCase();
      if (!answer || answer.includes("no relevant manual evidence")) return false;
      return Array.isArray(payload.evidence) && payload.evidence.length > 0;
    }

    function updateContext(questionText, payload) {
      if (!payload || !usefulResult(payload)) return;
      const evidence = Array.isArray(payload.evidence) ? payload.evidence : [];
      const firstEvidence = evidence.find((item) => item.manual_id) || {};
      const citations = Array.isArray(payload.citations) ? payload.citations : [];
      state.context = {
        current_manual_id: payload.manual_id || firstEvidence.manual_id || state.context.current_manual_id || null,
        current_manual_name: firstEvidence.manual || state.context.current_manual_name || "",
        current_subject: queryTerms(questionText).filter((term) => !["what", "where", "about", "tell"].includes(term)).slice(0, 8).join(" "),
        last_citations: citations,
        last_query_terms: queryTerms(questionText)
      };
    }

    async function queryManualGuide(originalText) {
      const rewritten = rewriteQuestion(originalText);
      const manualId = state.context && state.context.current_manual_id;
      if (manualId) {
        const manualResponse = await fetch("/manuals/" + encodeURIComponent(manualId) + "/query", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ question: rewritten, limit: 6 })
        });
        const manualData = await manualResponse.json().catch(() => ({}));
        if (manualResponse.ok && usefulResult(manualData)) {
          manualData.rewritten_question = rewritten;
          return manualData;
        }
        if (isAmbiguousFollowUp(originalText)) {
          return {
            answer: "I could not find relevant evidence for that in the selected/manual context.",
            confidence: "low",
            manual_id: manualId,
            citations: [],
            evidence: [],
            visual_assets: [],
            rejected_global_fallback: true
          };
        }
      }

      const response = await fetch("/manuals/query", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: rewritten, limit: 6 })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) return { answer: data.error || data.detail || "Manual search failed.", confidence: "low" };
      data.rewritten_question = rewritten;
      return data;
    }

    function evidenceUrl(item) {
      if (item.asset_url) return item.asset_url;
      if (item.manual_id && item.asset_id) return "/manuals/" + encodeURIComponent(item.manual_id) + "/assets/" + encodeURIComponent(item.asset_id);
      if (item.manual_id && item.page) return "/manuals/" + encodeURIComponent(item.manual_id) + "/pages/" + encodeURIComponent(item.page) + "/image";
      return "";
    }

    function appendMessage(role, payload) {
      const node = document.createElement("article");
      node.className = "message " + role;
      const text = document.createElement("div");
      text.textContent = typeof payload === "string" ? payload : payload.answer || "";
      node.appendChild(text);

      if (payload && typeof payload === "object") {
        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = "Confidence: " + (payload.confidence || "-");
        node.appendChild(meta);

        const citations = Array.isArray(payload.citations) ? payload.citations : [];
        if (citations.length) {
          const citationRow = document.createElement("div");
          citationRow.className = "citations";
          for (const citation of citations.slice(0, 6)) {
            const href = evidenceUrl({ ...citation, manual_id: citation.manual_id || payload.manual_id });
            if (!href) continue;
            const link = document.createElement("a");
            link.href = href;
            link.target = "_blank";
            link.rel = "noopener";
            link.textContent = "Page " + citation.page;
            citationRow.appendChild(link);
          }
          if (citationRow.childNodes.length) node.appendChild(citationRow);
        }

        const visualAssets = Array.isArray(payload.visual_assets) && payload.visual_assets.length
          ? payload.visual_assets
          : (Array.isArray(payload.evidence) ? payload.evidence : []);
        const grid = document.createElement("div");
        grid.className = "evidence";
        for (const item of visualAssets.slice(0, 4)) {
          const href = evidenceUrl(item);
          if (!href) continue;
          const card = document.createElement("a");
          card.className = "evidence-card";
          card.href = href;
          card.target = "_blank";
          card.rel = "noopener";
          const img = document.createElement("img");
          img.src = href;
          img.alt = "Evidence from page " + (item.page || "-");
          card.appendChild(img);
          const label = document.createElement("span");
          label.textContent = [item.type || "evidence", item.page ? "page " + item.page : ""].filter(Boolean).join(" | ");
          card.appendChild(label);
          grid.appendChild(card);
        }
        if (grid.childNodes.length) node.appendChild(grid);
      }

      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderHistory() {
      messages.textContent = "";
      for (const turn of state.history) appendMessage(turn.role, turn.payload);
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = question.value.trim();
      if (!text) return;
      question.value = "";
      send.disabled = true;
      const userTurn = { role: "user", payload: text };
      state.history.push(userTurn);
      appendMessage(userTurn.role, userTurn.payload);
      saveHistory();
      try {
        const payload = await queryManualGuide(text);
        updateContext(text, payload);
        state.history.push({ role: "assistant", payload });
        appendMessage("assistant", payload);
        saveHistory();
      } catch (error) {
        const payload = { answer: "Manual search is unreachable.", confidence: "low" };
        state.history.push({ role: "assistant", payload });
        appendMessage("assistant", payload);
        saveHistory();
      } finally {
        send.disabled = false;
        question.focus();
      }
    });

    renderHistory();
    if (!state.history.length) {
      appendMessage("assistant", { answer: "Ask a question and I will search all stored manuals and documents for cited evidence.", confidence: "-" });
    }
  </script>
</body>
</html>`;

const DEPOT_NOTE_HEADINGS = [
  "Safe access at height",
  "System characteristics notes",
  "Components that may require assistance for removal",
  "Restrictions to work areas or specific access permission required",
  "External hazardous work areas / ladder / scaffold / specific hazards",
  "Additional delivery notes",
  "Office notes",
  "Installer notes \u2014 boiler/controls",
  "Installer notes \u2014 flue",
  "Installer notes \u2014 gas/water",
  "Installer notes \u2014 disruption",
  "Installer notes \u2014 customer agreed actions",
  "Installer notes \u2014 special customer requirements / planned home improvement work",
];

const DEPOT_NOTES_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Depot Notes</title>
  <style>
    :root {
      color-scheme: light dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    body {
      margin: 0;
      min-height: 100dvh;
      background: #eef3f1;
      color: #17202a;
    }

    main {
      width: min(1080px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 18px 0 36px;
      display: grid;
      gap: 14px;
    }

    header,
    section,
    .note-card {
      border: 1px solid #d7dedb;
      border-radius: 8px;
      background: #ffffff;
    }

    header,
    section {
      padding: 16px;
    }

    h1,
    h2,
    h3 {
      margin: 0;
      letter-spacing: 0;
    }

    .composer {
      display: grid;
      gap: 12px;
    }

    textarea {
      width: 100%;
      box-sizing: border-box;
      min-height: 180px;
      padding: 12px;
      border: 1px solid #b9c5c0;
      border-radius: 8px;
      font: inherit;
      background: #ffffff;
      color: inherit;
      resize: vertical;
    }

    .change-box {
      min-height: 56px;
    }

    button {
      min-height: 40px;
      padding: 0 14px;
      border: 0;
      border-radius: 8px;
      background: #146c5c;
      color: #ffffff;
      font: inherit;
      font-weight: 800;
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

    .cards {
      display: grid;
      gap: 12px;
    }

    .empty-state,
    .error-panel {
      padding: 12px;
      border: 1px solid #d7dedb;
      border-radius: 8px;
      background: #f8faf9;
      color: #627083;
    }

    .error-panel {
      border-color: #f2b8b5;
      background: #fff4f3;
      color: #7d2621;
    }

    .note-card {
      display: grid;
      gap: 10px;
      padding: 14px;
    }

    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }

    .note-text {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 10px;
      border: 1px solid #d7dedb;
      border-radius: 8px;
      background: #f8faf9;
    }

    .change-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: end;
    }

    #status {
      color: #627083;
      min-height: 22px;
    }

    @media (prefers-color-scheme: dark) {
      body {
        background: #10151b;
        color: #edf2f7;
      }

      header,
      section,
      .note-card,
      textarea {
        background: #171d25;
        border-color: #344052;
      }

      .note-text {
        background: #10151b;
        border-color: #344052;
      }

      .empty-state {
        background: #10151b;
        border-color: #344052;
      }

      .error-panel {
        background: #2a1718;
        border-color: #6f3030;
        color: #ffd7d4;
      }

      button.secondary {
        background: #263241;
        color: #edf2f7;
      }
    }

    @media (max-width: 720px) {
      .card-head,
      .change-row {
        grid-template-columns: 1fr;
        display: grid;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Depot Notes</h1>
      <div id="status">Paste a transcript and generate one editable card per depot-note heading.</div>
    </header>

    <section class="composer">
      <h2>Transcript</h2>
      <textarea id="transcript" placeholder="Paste the customer/job transcript here..."></textarea>
      <button id="generate" type="button">Generate depot notes</button>
    </section>

    <section>
      <h2>Generated notes</h2>
      <div id="cards" class="cards"></div>
    </section>
  </main>
  <script>
    const headings = ${JSON.stringify(DEPOT_NOTE_HEADINGS)};
    const transcript = document.getElementById("transcript");
    const generate = document.getElementById("generate");
    const cards = document.getElementById("cards");
    const statusEl = document.getElementById("status");
    const notes = new Map();

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function showEmpty() {
      notes.clear();
      cards.textContent = "";
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "No depot notes generated yet.";
      cards.appendChild(empty);
    }

    function showError(data, fallback, clearCards = true) {
      if (clearCards) {
        notes.clear();
        cards.textContent = "";
      }
      const existing = cards.querySelector(".error-panel");
      if (existing) existing.remove();
      const panel = document.createElement("div");
      panel.className = "error-panel";
      const endpoint = data && data.endpoint ? data.endpoint : "unknown";
      const status = data && data.status ? String(data.status) : "unknown";
      const diagnostic = data && data.diagnostic
        ? data.diagnostic
        : "Check the Worker gateway endpoint and model configuration, then retry.";
      panel.textContent = (data && (data.error || data.detail)) || fallback || "Generation failed";
      panel.appendChild(document.createElement("br"));
      panel.appendChild(document.createTextNode("Endpoint: " + endpoint + " | Status: " + status));
      panel.appendChild(document.createElement("br"));
      panel.appendChild(document.createTextNode("Next: " + diagnostic));
      cards.prepend(panel);
      setStatus((data && (data.error || data.detail)) || fallback || "Generation failed");
    }

    function renderCards(sections) {
      cards.textContent = "";
      for (const heading of headings) {
        const section = sections.find((item) => item.heading === heading) || { heading, text: "Not mentioned" };
        notes.set(heading, section.text || "Not mentioned");
        const card = document.createElement("article");
        card.className = "note-card";
        const head = document.createElement("div");
        head.className = "card-head";
        const title = document.createElement("h3");
        title.textContent = heading;
        const copy = document.createElement("button");
        copy.type = "button";
        copy.className = "secondary";
        copy.textContent = "Copy";
        copy.addEventListener("click", async () => {
          await navigator.clipboard.writeText(notes.get(heading) || "");
          setStatus("Copied: " + heading);
        });
        head.appendChild(title);
        head.appendChild(copy);
        const text = document.createElement("div");
        text.className = "note-text";
        text.textContent = notes.get(heading);
        const changeRow = document.createElement("div");
        changeRow.className = "change-row";
        const change = document.createElement("textarea");
        change.className = "change-box";
        change.placeholder = "Request changes to this section...";
        const apply = document.createElement("button");
        apply.type = "button";
        apply.textContent = "Apply change";
        apply.addEventListener("click", async () => {
          const request = change.value.trim();
          if (!request) return;
          apply.disabled = true;
          setStatus("Revising: " + heading);
          try {
            const response = await fetch("/depot-notes/revise", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({
                transcript: transcript.value,
                heading,
                currentText: notes.get(heading),
                changeRequest: request
              })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
              showError(data, "Revision failed", false);
              return;
            }
            notes.set(heading, data.text || "Not mentioned");
            text.textContent = notes.get(heading);
            change.value = "";
            setStatus("Updated: " + heading);
          } catch (error) {
            setStatus(error.message || "Revision failed");
          } finally {
            apply.disabled = false;
          }
        });
        changeRow.appendChild(change);
        changeRow.appendChild(apply);
        card.appendChild(head);
        card.appendChild(text);
        card.appendChild(changeRow);
        cards.appendChild(card);
      }
    }

    generate.addEventListener("click", async () => {
      const text = transcript.value.trim();
      if (!text) {
        setStatus("Paste a transcript first.");
        return;
      }
      generate.disabled = true;
      setStatus("Generating depot notes...");
      try {
        const response = await fetch("/depot-notes/generate", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ transcript: text })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          showError(data, "Generation failed");
          return;
        }
        renderCards(Array.isArray(data.sections) ? data.sections : []);
        setStatus("Generated " + headings.length + " editable sections.");
      } catch (error) {
        showError({ error: error.message || "Generation failed" }, "Generation failed");
      } finally {
        generate.disabled = false;
      }
    });

    showEmpty();
  </script>
</body>
</html>`;

const DEV_PAGE = `<!doctype html>
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

    .manual-chat {
      display: grid;
      gap: 12px;
      max-height: 520px;
      overflow: auto;
      padding: 4px 0;
    }

    .manual-message {
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid #d8dde6;
      border-radius: 8px;
      background: #ffffff;
    }

    .manual-message.user {
      border-color: #9fb7ce;
      background: #f7fbff;
    }

    .manual-meta,
    .manual-citations {
      color: #627083;
      font-size: 13px;
    }

    .manual-citations {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .manual-citations a {
      color: #146c5c;
      font-weight: 700;
    }

    .manual-evidence-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }

    .manual-evidence {
      display: grid;
      gap: 6px;
      padding: 8px;
      border: 1px solid #d8dde6;
      border-radius: 8px;
      background: #f8fafc;
      font-size: 13px;
    }

    .manual-evidence img {
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: contain;
      border: 1px solid #d8dde6;
      border-radius: 6px;
      background: #ffffff;
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
      .manual-message,
      select,
      input[type="file"],
      textarea {
        background: #171d25;
        border-color: #344052;
      }

      .manual-message.user,
      .manual-evidence {
        background: #10151b;
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
          <label>
            Attach photographed page
            <input id="manual-image" class="manual-file" type="file" accept="image/*">
          </label>
          <button id="manual-refresh" class="secondary" type="button">Refresh manuals</button>
        </section>

        <section class="panel">
          <strong>Response</strong>
          <div id="response" class="response manual-chat">Ready.</div>
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
      lastHealth: null,
      manualHistory: []
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
      manualImage: document.getElementById("manual-image"),
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

    function manualEvidenceUrl(manualId, item) {
      if (item.asset_url) return item.asset_url;
      if (item.type === "page_render" && item.page) return "/manuals/" + encodeURIComponent(manualId) + "/pages/" + encodeURIComponent(item.page) + "/image";
      if (item.asset_id) return "/manuals/" + encodeURIComponent(manualId) + "/assets/" + encodeURIComponent(item.asset_id);
      if (item.page) return "/manuals/" + encodeURIComponent(manualId) + "/pages/" + encodeURIComponent(item.page) + "/image";
      return "";
    }

    function appendManualMessage(role, payload) {
      if (els.response.textContent === "Ready.") els.response.textContent = "";
      const message = document.createElement("article");
      message.className = "manual-message " + role;
      const body = document.createElement("div");
      body.textContent = typeof payload === "string" ? payload : payload.answer || "";
      message.appendChild(body);

      if (payload && typeof payload === "object") {
        const meta = document.createElement("div");
        meta.className = "manual-meta";
        meta.textContent = "Confidence: " + safeText(payload.confidence);
        message.appendChild(meta);

        const evidence = Array.isArray(payload.evidence) ? payload.evidence.slice(0, 4) : [];
        const citations = document.createElement("div");
        citations.className = "manual-citations";
        for (const item of evidence) {
          const href = manualEvidenceUrl(payload.manual_id, item);
          if (!href) continue;
          const link = document.createElement("a");
          link.href = href;
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = "Page " + item.page + " " + (item.type || "evidence");
          citations.appendChild(link);
        }
        if (citations.childNodes.length) message.appendChild(citations);

        const grid = document.createElement("div");
        grid.className = "manual-evidence-grid";
        for (const item of evidence) {
          const href = manualEvidenceUrl(payload.manual_id, item);
          const card = document.createElement("a");
          card.className = "manual-evidence";
          card.href = href || "#";
          card.target = "_blank";
          card.rel = "noopener";
          if (href && (item.type === "page_render" || item.type === "image")) {
            const img = document.createElement("img");
            img.src = href;
            img.alt = "Evidence from page " + item.page;
            card.appendChild(img);
          }
          const caption = document.createElement("span");
          caption.textContent = [
            item.type || "evidence",
            item.page ? "page " + item.page : "",
            item.confidence ? item.confidence : ""
          ].filter(Boolean).join(" | ");
          card.appendChild(caption);
          const snippet = item.snippet || item.description || "";
          if (snippet) {
            const text = document.createElement("small");
            text.textContent = snippet.length > 180 ? snippet.slice(0, 180) + "..." : snippet;
            card.appendChild(text);
          }
          grid.appendChild(card);
        }
        if (grid.childNodes.length) message.appendChild(grid);
      }

      els.response.appendChild(message);
      els.response.scrollTop = els.response.scrollHeight;
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
      const image = els.manualImage.files && els.manualImage.files[0];
      if (!manualId) {
        els.response.classList.add("error-text");
        els.response.textContent = "Select or upload a manual first.";
        return;
      }
      if (!question && !image) {
        els.response.classList.add("error-text");
        els.response.textContent = "Question or photographed page is required for Manual Ripper.";
        return;
      }
      const request = { question, limit: 5 };
      els.send.disabled = true;
      els.response.classList.remove("error-text");
      appendManualMessage("user", question || "Attached photographed manual page.");
      els.prompt.value = "";
      els.rawRequest.textContent = pretty({ manual_id: manualId, ...request, image: image ? image.name : undefined });
      try {
        let result;
        if (image) {
          const formData = new FormData();
          formData.append("question", question);
          formData.append("image", image);
          result = await fetch("/manuals/" + encodeURIComponent(manualId) + "/query-image", {
            method: "POST",
            body: formData
          });
          els.manualImage.value = "";
        } else {
          result = await fetch("/manuals/" + encodeURIComponent(manualId) + "/query", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(request)
          });
        }
        const data = await result.json().catch(() => ({}));
        els.rawResponse.textContent = pretty(data);
        if (!result.ok) throw new Error(data.error || data.detail || "Manual query failed");
        appendManualMessage("assistant", data);
        state.manualHistory.push({ role: "user", content: question });
        state.manualHistory.push({ role: "assistant", content: data.answer || "", evidence: data.evidence || [] });
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
        appendManualMessage("assistant", error.message || "Manual Ripper service is unreachable.");
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
      state.manualHistory = [];
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

const ADMIN_PAGE = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manual Ripper Admin</title>
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
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 20px 0 40px;
      display: grid;
      gap: 16px;
    }

    header,
    section,
    .doc {
      border: 1px solid #d8dde6;
      border-radius: 8px;
      background: #ffffff;
    }

    header,
    section {
      padding: 16px;
    }

    h1,
    h2 {
      margin: 0;
      letter-spacing: 0;
    }

    .upload {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }

    label {
      display: grid;
      gap: 6px;
      font-weight: 700;
    }

    input,
    button {
      min-height: 42px;
      box-sizing: border-box;
      border-radius: 8px;
      font: inherit;
    }

    input {
      padding: 8px 10px;
      border: 1px solid #c8ced8;
      background: #ffffff;
      color: inherit;
    }

    button {
      border: 0;
      padding: 0 16px;
      background: #146c5c;
      color: #ffffff;
      font-weight: 800;
      cursor: pointer;
    }

    button.secondary {
      background: #e8edf2;
      color: #17202a;
    }

    button.danger {
      background: #b42318;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }

    .docs {
      display: grid;
      gap: 10px;
    }

    .doc {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      padding: 12px;
      align-items: center;
    }

    .doc-title {
      font-weight: 800;
      overflow-wrap: anywhere;
    }

    .doc-meta {
      color: #627083;
      font-size: 13px;
    }

    .doc-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: end;
    }

    #status {
      color: #627083;
      min-height: 24px;
    }

    @media (prefers-color-scheme: dark) {
      body {
        background: #10151b;
        color: #edf2f7;
      }

      header,
      section,
      .doc,
      input {
        background: #171d25;
        border-color: #344052;
      }

      button.secondary {
        background: #263241;
        color: #edf2f7;
      }
    }

    @media (max-width: 760px) {
      .upload,
      .doc {
        grid-template-columns: 1fr;
      }

      .doc-actions {
        justify-content: start;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Document Manager</h1>
      <div id="status">Loading documents...</div>
    </header>

    <section>
      <h2>Upload PDF</h2>
      <form id="upload-form" class="upload">
        <label>
          PDF document
          <input id="pdf" type="file" accept="application/pdf,.pdf">
        </label>
        <button id="upload" type="submit">Upload</button>
      </form>
    </section>

    <section>
      <h2>Stored Documents</h2>
      <div id="docs" class="docs"></div>
    </section>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const docsEl = document.getElementById("docs");
    const uploadForm = document.getElementById("upload-form");
    const pdf = document.getElementById("pdf");
    const upload = document.getElementById("upload");
    const adminKey = new URL(location.href).searchParams.get("admin_key") || "";

    function adminUrl(path) {
      return adminKey ? path + "?admin_key=" + encodeURIComponent(adminKey) : path;
    }

    function setStatus(text) {
      statusEl.textContent = text;
    }

    function docName(doc) {
      return [doc.manufacturer, doc.model].filter(Boolean).join(" ") || doc.filename || doc.id;
    }

    async function loadDocs() {
      setStatus("Loading documents...");
      try {
        const response = await fetch("/manuals", { cache: "no-store" });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.detail || "Unable to load documents");
        const manuals = Array.isArray(data.manuals) ? data.manuals : [];
        docsEl.textContent = "";
        if (!manuals.length) {
          docsEl.textContent = "No documents stored yet.";
        }
        for (const doc of manuals) {
          const row = document.createElement("article");
          row.className = "doc";
          const body = document.createElement("div");
          const title = document.createElement("div");
          title.className = "doc-title";
          title.textContent = docName(doc);
          const meta = document.createElement("div");
          meta.className = "doc-meta";
          meta.textContent = [
            "status: " + (doc.extraction_status || "-"),
            doc.page_count ? "pages: " + doc.page_count : "",
            doc.uploaded_at ? "uploaded: " + doc.uploaded_at : ""
          ].filter(Boolean).join(" | ");
          body.appendChild(title);
          body.appendChild(meta);
          row.appendChild(body);

          const actions = document.createElement("div");
          actions.className = "doc-actions";
          const extract = document.createElement("button");
          extract.type = "button";
          extract.textContent = "Re-extract";
          extract.addEventListener("click", () => extractDoc(doc.id));
          const disable = document.createElement("button");
          disable.type = "button";
          disable.className = "secondary";
          disable.textContent = "Disable";
          disable.addEventListener("click", () => manageDoc(doc.id, "disable"));
          const del = document.createElement("button");
          del.type = "button";
          del.className = "danger";
          del.textContent = "Delete";
          del.addEventListener("click", () => manageDoc(doc.id, "delete"));
          actions.appendChild(extract);
          actions.appendChild(disable);
          actions.appendChild(del);
          row.appendChild(actions);
          docsEl.appendChild(row);
        }
        setStatus("Loaded " + manuals.length + " document" + (manuals.length === 1 ? "" : "s") + ".");
      } catch (error) {
        docsEl.textContent = "";
        setStatus(error.message || "Manual Ripper service is unreachable.");
      }
    }

    async function extractDoc(id) {
      setStatus("Extracting document...");
      const response = await fetch("/manuals/" + encodeURIComponent(id) + "/extract", { method: "POST" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) setStatus(data.error || data.detail || "Extraction failed.");
      await loadDocs();
    }

    async function manageDoc(id, action) {
      setStatus(action === "delete" ? "Deleting document..." : "Disabling document...");
      const response = await fetch(adminUrl("/admin/manuals/" + encodeURIComponent(id)), {
        method: action === "delete" ? "DELETE" : "PATCH",
        headers: action === "delete" ? undefined : { "content-type": "application/json" },
        body: action === "delete" ? undefined : JSON.stringify({ disabled: true })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) setStatus(data.error || data.detail || "Document action failed.");
      await loadDocs();
    }

    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const file = pdf.files && pdf.files[0];
      if (!file) {
        setStatus("Choose a PDF first.");
        return;
      }
      const formData = new FormData();
      formData.append("file", file);
      upload.disabled = true;
      setStatus("Uploading PDF...");
      try {
        const response = await fetch("/manuals/upload", { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.detail || "Upload failed.");
        setStatus("Uploaded. Extracting...");
        await fetch("/manuals/" + encodeURIComponent(data.manual.id) + "/extract", { method: "POST" });
        pdf.value = "";
        await loadDocs();
      } catch (error) {
        setStatus(error.message || "Upload failed.");
      } finally {
        upload.disabled = false;
      }
    });

    loadDocs();
  </script>
</body>
</html>`;

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

if (typeof addEventListener === "function") {
  addEventListener("fetch", (event) => {
    event.respondWith(handleRequest(event.request, globalThis));
  });
}

async function handleRequest(request, env) {
  const url = new URL(request.url);

  if (request.method === "GET" && url.pathname === "/") {
    return html(WELCOME_PAGE);
  }

  if (request.method === "GET" && url.pathname === "/chat") {
    return html(PUBLIC_CHAT_PAGE);
  }

  if (request.method === "GET" && url.pathname === "/depot-notes") {
    return html(DEPOT_NOTES_PAGE);
  }

  if (request.method === "GET" && url.pathname === "/depot-notes/debug") {
    const blocked = requireAdmin(request, env);
    if (blocked) return blocked;
    return handleDepotNotesDebug(env);
  }

  if (request.method === "POST" && url.pathname === "/depot-notes/generate") {
    return handleDepotNotesGenerate(request, env);
  }

  if (request.method === "POST" && url.pathname === "/depot-notes/revise") {
    return handleDepotNotesRevise(request, env);
  }

  if (request.method === "GET" && url.pathname === "/dev") {
    const blocked = requireAdmin(request, env);
    if (blocked) return blocked;
    return html(DEV_PAGE);
  }

  if (request.method === "GET" && url.pathname === "/admin") {
    const blocked = requireAdmin(request, env);
    if (blocked) return blocked;
    return html(ADMIN_PAGE);
  }

  if (url.pathname.startsWith("/admin/manuals/")) {
    const blocked = requireAdmin(request, env);
    if (blocked) return blocked;
    return handleManualProxy(request, env, url, { stripAdminPrefix: true });
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

function html(page) {
  return new Response(page, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "no-store",
      },
  });
}

function requireAdmin(request, env) {
  if (!env.ADMIN_KEY) return null;
  const url = new URL(request.url);
  const supplied = request.headers.get("x-admin-key") || url.searchParams.get("admin_key");
  if (supplied === env.ADMIN_KEY) return null;
  return json({ error: "Admin access denied" }, 401);
}

async function handleManualProxy(request, env, url, options = {}) {
  if (!env.MANUAL_RIPPER_BASE_URL) {
    return json({
      error: "Manual Ripper service is not configured",
      detail: "Set MANUAL_RIPPER_BASE_URL to the private service URL or Cloudflare Tunnel route.",
    }, 503);
  }

  const started = Date.now();
  const pathname = options.stripAdminPrefix ? url.pathname.replace(/^\/admin/, "/admin") : url.pathname;
  const target = buildGatewayUrl(env.MANUAL_RIPPER_BASE_URL, pathname + url.search);
  const headers = {};
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    });
    const upstreamType = upstream.headers.get("content-type") || "";
    if (!upstreamType.includes("application/json")) {
      return new Response(upstream.body, {
        status: upstream.status,
        headers: {
          "content-type": upstreamType || "application/octet-stream",
          "cache-control": upstream.headers.get("cache-control") || "no-store",
          ...corsHeaders(),
        },
      });
    }
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

async function handleDepotNotesGenerate(request, env) {
  if (!hasGatewayConfig(env)) {
    return json({ error: "LLM gateway is not configured" }, 500);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON", detail: "Expected JSON body" }, 400);
  }

  const transcript = typeof body.transcript === "string" ? body.transcript.trim() : "";
  if (!transcript) {
    return json({ error: "Transcript is required" }, 400);
  }

  const prompt = [
    "Create depot notes from the transcript.",
    "Return strict JSON only with this shape: {\"sections\":[{\"heading\":\"...\",\"text\":\"...\"}]}",
    "Use exactly these headings and no others: " + DEPOT_NOTE_HEADINGS.join(" | "),
    "Each generated section uses short practical bullets.",
    "Use ; as the line-break separator for depot compatibility.",
    "Keep text short enough for engineers to scan quickly.",
    "Avoid repeating generic T&Cs.",
    "Use \"Not mentioned\" only when there is no relevant job-specific information.",
    "Never invent information not present in the transcript.",
    "Transcript:",
    transcript,
  ].join("\n");

  const endpoint = "/v1/json";
  const result = await gatewayFetch(env, endpoint, {
    method: "POST",
    auth: true,
    body: {
      model: env.DAEDALUS_LLM_MODEL,
      prompt,
      temperature: 0,
      schema: {
        sections: DEPOT_NOTE_HEADINGS.map((heading) => ({ heading, text: "string" })),
      },
    },
    timeoutMs: 90000,
  });

  if (!result.ok) {
    return json(depotGatewayDiagnostic(result, endpoint), result.status || 502);
  }

  return json({ sections: normalizeDepotSections(extractGatewayResponse(result.body)) });
}

async function handleDepotNotesRevise(request, env) {
  if (!hasGatewayConfig(env)) {
    return json({ error: "LLM gateway is not configured" }, 500);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON", detail: "Expected JSON body" }, 400);
  }

  const transcript = typeof body.transcript === "string" ? body.transcript.trim() : "";
  const heading = typeof body.heading === "string" ? body.heading.trim() : "";
  const currentText = typeof body.currentText === "string" ? body.currentText.trim() : "";
  const changeRequest = typeof body.changeRequest === "string" ? body.changeRequest.trim() : "";
  if (!transcript || !heading || !changeRequest || !DEPOT_NOTE_HEADINGS.includes(heading)) {
    return json({ error: "Transcript, valid heading, and change request are required" }, 400);
  }

  const prompt = [
    "Revise one depot-note section only.",
    "Return strict JSON only with this shape: {\"heading\":\"" + heading + "\",\"text\":\"...\"}",
    "Section-level change request must only alter this section: " + heading,
    "Retain facts from the transcript unless the user explicitly asks to remove or reword them.",
    "Do not introduce facts absent from the transcript or user change request.",
    "Use short practical bullets.",
    "Use ; as the line-break separator for depot compatibility.",
    "Keep it short enough for engineers to scan quickly.",
    "Use \"Not mentioned\" only when there is no relevant job-specific information.",
    "Heading: " + heading,
    "Current section text: " + currentText,
    "User change request: " + changeRequest,
    "Transcript:",
    transcript,
  ].join("\n");

  const endpoint = "/v1/json";
  const result = await gatewayFetch(env, endpoint, {
    method: "POST",
    auth: true,
    body: {
      model: env.DAEDALUS_LLM_MODEL,
      prompt,
      temperature: 0,
      schema: { heading, text: "string" },
    },
    timeoutMs: 90000,
  });

  if (!result.ok) {
    return json(depotGatewayDiagnostic(result, endpoint), result.status || 502);
  }

  const parsed = parseJsonFromModel(extractGatewayResponse(result.body));
  return json({
    heading,
    text: sanitizeDepotText(parsed && typeof parsed.text === "string" ? parsed.text : String(extractGatewayResponse(result.body) || "")),
  });
}

function normalizeDepotSections(value) {
  const parsed = parseJsonFromModel(value);
  const source = parsed && Array.isArray(parsed.sections) ? parsed.sections : [];
  return DEPOT_NOTE_HEADINGS.map((heading) => {
    const match = source.find((item) => item && item.heading === heading);
    return {
      heading,
      text: sanitizeDepotText(match && typeof match.text === "string" ? match.text : "Not mentioned"),
    };
  });
}

function sanitizeDepotText(value) {
  const text = String(value || "").trim();
  if (!text) return "Not mentioned";
  return text
    .split(/\r?\n+/)
    .map((line) => line.replace(/^[\s*\u2022-]+/, "").trim())
    .filter(Boolean)
    .join("; ");
}

function depotGatewayDiagnostic(result, endpoint) {
  const failureKind = depotFailureKind(result);
  return {
    error: classifyGatewayError(result),
    failureKind,
    endpoint,
    status: result.status || 0,
    diagnostic: depotDiagnosticMessage(failureKind, endpoint),
    safeBody: safeGatewayBody(result.body),
  };
}

async function handleDepotNotesDebug(env) {
  const endpoint = "/v1/json";
  const configuredModel = env.DAEDALUS_LLM_MODEL || null;
  const gatewayOrigin = safeOrigin(env.DAEDALUS_LLM_GATEWAY_URL);
  if (!hasGatewayConfig(env)) {
    return json({
      ok: false,
      config: {
        gatewayConfigured: Boolean(env.DAEDALUS_LLM_GATEWAY_URL),
        gatewayOrigin,
        apiKeyConfigured: Boolean(env.DAEDALUS_LLM_API_KEY),
        modelConfigured: Boolean(env.DAEDALUS_LLM_MODEL),
        model: configuredModel,
      },
      route: endpoint,
      failureKind: "config_missing",
      diagnostic: "Set DAEDALUS_LLM_GATEWAY_URL, DAEDALUS_LLM_API_KEY, and DAEDALUS_LLM_MODEL.",
    }, 500);
  }

  const health = await gatewayFetch(env, "/health", { method: "GET", auth: false, timeoutMs: 8000 });
  const models = await gatewayFetch(env, "/models", { method: "GET", auth: true, timeoutMs: 12000 });
  const modelNames = models.ok && Array.isArray(models.body.models)
    ? models.body.models.map((model) => model && (model.name || model.model)).filter(Boolean)
    : [];
  const modelAvailable = configuredModel ? modelNames.includes(configuredModel) : Boolean(models.body.defaultModel);
  const jsonProbe = await gatewayFetch(env, endpoint, {
    method: "POST",
    auth: true,
    body: {
      model: configuredModel,
      prompt: "Return this JSON exactly: {\"ok\":true}",
      temperature: 0,
      schema: { ok: true },
    },
    timeoutMs: 25000,
  });
  const failureKind = !health.ok
    ? depotFailureKind(health)
    : !models.ok
      ? depotFailureKind(models)
      : !modelAvailable
        ? "model_missing"
        : !jsonProbe.ok
          ? depotFailureKind(jsonProbe)
          : null;

  return json({
    ok: !failureKind,
    config: {
      gatewayConfigured: Boolean(env.DAEDALUS_LLM_GATEWAY_URL),
      gatewayOrigin,
      apiKeyConfigured: Boolean(env.DAEDALUS_LLM_API_KEY),
      modelConfigured: Boolean(env.DAEDALUS_LLM_MODEL),
      model: configuredModel,
    },
    route: endpoint,
    health: diagnosticFromResult(health),
    models: {
      ...diagnosticFromResult(models),
      defaultModel: models.body.defaultModel || configuredModel,
      configuredModel,
      configuredModelAvailable: modelAvailable,
      modelCount: modelNames.length,
    },
    jsonProbe: {
      ...diagnosticFromResult(jsonProbe),
      failureKind: jsonProbe.ok ? undefined : depotFailureKind(jsonProbe),
    },
    failureKind,
    diagnostic: failureKind ? depotDiagnosticMessage(failureKind, endpoint) : "Depot Notes JSON route is reachable and the configured model is available.",
  }, failureKind ? 502 : 200);
}

function depotFailureKind(result) {
  const bodyText = JSON.stringify(result && result.body ? result.body : {}).toLowerCase();
  if (!result || result.status === 0) return "gateway_unreachable";
  if (result.status === 401 || result.status === 403) return "auth_failed";
  if (result.status === 404 || result.status === 405) return "route_missing";
  if (result.status === 408 || result.status === 504) return "upstream_timeout";
  if (result.status === 524) return "cloudflare_timeout";
  if (bodyText.includes("model") && (bodyText.includes("not found") || bodyText.includes("unavailable") || bodyText.includes("missing"))) {
    return "model_missing";
  }
  return "upstream_error";
}

function depotDiagnosticMessage(kind, endpoint) {
  if (kind === "config_missing") return "Worker environment is missing gateway URL, API key, or model.";
  if (kind === "gateway_unreachable") return "The Worker could not reach the configured LLM gateway origin.";
  if (kind === "auth_failed") return "The LLM gateway rejected the Worker API key.";
  if (kind === "route_missing") return "The configured LLM gateway does not serve " + endpoint + ". Deploy/restart the gateway code that includes this route.";
  if (kind === "model_missing") return "The configured model is not listed by /models or the upstream reported that the model is unavailable.";
  if (kind === "upstream_timeout") return "The LLM gateway accepted the request but the upstream model timed out before returning JSON.";
  if (kind === "cloudflare_timeout") return "Cloudflare timed out waiting for the Worker/upstream response.";
  return "The LLM gateway returned an upstream error for " + endpoint + ".";
}

function parseJsonFromModel(value) {
  if (value && typeof value === "object") return value;
  const text = String(value || "").trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
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
  const kind = depotFailureKind(result);
  if (kind === "route_missing") return "Gateway route missing";
  if (kind === "model_missing") return "Model unavailable";
  if (kind === "upstream_timeout") return "Upstream timeout";
  if (kind === "cloudflare_timeout") return "Cloudflare timeout";
  if (kind === "gateway_unreachable") return "Gateway unreachable";
  if (kind === "auth_failed") return "Authentication failed";
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
    "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "access-control-allow-headers": "content-type,x-admin-key",
  };
}

if (typeof module !== "undefined") {
  module.exports = { handleRequest };
}
