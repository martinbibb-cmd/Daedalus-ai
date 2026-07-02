# Daedalus-ai

## daedalus-llm-gateway

Fastify API gateway for private Ollama access on the Daedalus network.

Apps should call this gateway only. Do not expose raw Ollama publicly.

## Pet Llama v0.2 Engineering Console

`petllama` is a Cloudflare Worker UI for testing the Daedalus gateway from a browser without exposing gateway secrets. It is an engineering console, not a ChatGPT clone.

Architecture:

```text
Browser petllama UI
  -> POST /chat on the petllama Worker
  -> Daedalus LLM gateway at https://ai.atlas-phm.uk
  -> private Ollama backend
```

The browser only calls the Worker:

- `GET /` serves the console UI.
- `GET /health` returns Worker version, non-secret configuration diagnostics, gateway reachability, tunnel reachability, and LLM self-test state.
- `GET /models` returns the gateway model list through the Worker.
- `POST /chat` accepts the selected mode, model, temperature, optional schema, and prompt, then the Worker calls the private gateway.

The Worker supports these modes:

- Chat: calls `/v1/chat`, with fallback to `/v1/summarise` if the chat endpoint is unavailable.
- Summarise: calls `/v1/summarise`.
- Extract evidence: calls `/v1/extract-evidence`.
- JSON: calls `/v1/json` with an optional schema from the console.
- Self-test: calls `GET /v1/self-test`.

The console includes:

- model selector populated from `/models`
- temperature control from `0.0` to `1.5`
- formatted response panel
- collapsible diagnostics and trace panels
- hidden-by-default raw request and raw response JSON
- health banner that refreshes every 30 seconds

Secrets stay server-side. The Worker sends `x-daedalus-api-key` to the gateway and never exposes it to browser JavaScript.

## Manual Ripper: Local Manual Ingestion/RAG

Manual Ripper is local document ingestion and retrieval augmented generation, not model training.

Training changes model weights. Manual Ripper keeps the model unchanged and instead stores boiler/heating PDFs locally, extracts page text, retrieves relevant pages, and asks the gateway to answer using only that evidence.

Architecture:

```text
Pet Llama Worker
  -> Manual Ripper service on the Daedalus VM
  -> /srv/daedalus/manuals local storage
  -> Daedalus LLM Gateway
  -> Ollama
```

Manual data is not stored in Cloudflare. The Worker is a thin proxy to the private Manual Ripper service.

Storage layout:

```text
/srv/daedalus/manuals/
  originals/
  extracted/
  indexes/
  metadata.sqlite
```

Manual Ripper endpoints:

- `GET /health`
- `GET /manuals`
- `POST /manuals/upload`
- `GET /manuals/{id}`
- `POST /manuals/{id}/extract`
- `POST /manuals/{id}/query`
- `POST /manuals/search`

Manual Ripper service setup:

```bash
cd manual-ripper
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin manual-ripper || true
sudo bash scripts/bootstrap-storage.sh
```

Create `/etc/daedalus-manual-ripper.env`:

```bash
MANUAL_RIPPER_STORAGE_ROOT=/srv/daedalus/manuals
DAEDALUS_LLM_GATEWAY_URL=https://ai.atlas-phm.uk
DAEDALUS_LLM_API_KEY=replace-with-secret
DAEDALUS_LLM_MODEL=llama3.2:3b
HOST=127.0.0.1
PORT=8791
```

Install systemd unit:

```bash
sudo cp manual-ripper/systemd/daedalus-manual-ripper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daedalus-manual-ripper
```

Worker configuration:

```toml
MANUAL_RIPPER_BASE_URL = "https://manuals.atlas-phm.uk"
```

Expose Manual Ripper privately, preferably through Cloudflare Tunnel or another controlled private route. Do not expose it as an unauthenticated public internet service.

Manual query response shape:

```json
{
  "answer": "string",
  "manual_id": "string",
  "evidence": [
    {
      "page": 1,
      "snippet": "string",
      "confidence": "low|medium|high"
    }
  ]
}
```

Required Cloudflare secret:

```bash
npx wrangler secret put DAEDALUS_LLM_API_KEY
```

Do not commit `DAEDALUS_LLM_API_KEY` to the repo. Non-secret Worker vars are set in `wrangler.toml`:

```toml
DAEDALUS_LLM_GATEWAY_URL = "https://ai.atlas-phm.uk"
DAEDALUS_LLM_MODEL = "llama3.2:3b"
```

Manual deploy flow:

```bash
git pull origin main
npm install
npm run deploy
```

Preferred Daedalus VM deploy flow:

```bash
cd /home/martin/Daedalus-ai
bash scripts/deploy-petllama-from-vm.sh
```

The helper fast-forwards `main`, runs tests, deploys the Worker, restarts Manual Ripper when the systemd service exists, and prints health plus Depot Notes diagnostics. It requires `CLOUDFLARE_API_TOKEN` to be set in the VM shell.

Avoid exposing this as a public chat command. If an automated admin endpoint is needed later, protect it with a separate admin-only secret and fixed allowlisted actions.

## Configuration

Create `.env`:

```bash
DAEDALUS_LLM_API_KEY=replace-with-a-long-random-secret
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=llama3.2:3b
HOST=0.0.0.0
PORT=8787
```

Required environment variables:

- `DAEDALUS_LLM_API_KEY`: shared API key required in `x-daedalus-api-key`
- `OLLAMA_BASE_URL`: private Ollama base URL. Use `http://127.0.0.1:11434` when the gateway runs on the same host as Ollama.
- `DEFAULT_MODEL`: default Ollama model, for example `llama3.2:3b`

## Install and Run

```bash
npm install
npm start
```

For another machine on Tailscale to reach the gateway, bind to the host's Tailscale interface or all interfaces behind a firewall:

```bash
HOST=0.0.0.0 PORT=8787 npm start
```

## App Configuration

Daedalus and Asguardian should use the gateway only:

```bash
DAEDALUS_LLM_BASE_URL=http://daedalus-ai:8787
DAEDALUS_LLM_API_KEY=<same-long-secret>
DAEDALUS_LLM_MODEL=llama3.2:3b
```

Do not configure apps to call `:11434` directly.

## Endpoints

`GET /health` is unauthenticated for service checks.

All other endpoints require:

```http
x-daedalus-api-key: <DAEDALUS_LLM_API_KEY>
content-type: application/json
```

### GET /health

```bash
curl http://127.0.0.1:8787/health
```

### GET /models

```bash
curl http://127.0.0.1:8787/models \
  -H "x-daedalus-api-key: $DAEDALUS_LLM_API_KEY"
```

### GET /v1/self-test

Protected diagnostic check that asks the configured Ollama backend to generate through `DEFAULT_MODEL`.

```bash
curl http://127.0.0.1:8787/v1/self-test \
  -H "x-daedalus-api-key: $DAEDALUS_LLM_API_KEY"
```

### POST /v1/json

```bash
curl http://127.0.0.1:8787/v1/json \
  -H "content-type: application/json" \
  -H "x-daedalus-api-key: $DAEDALUS_LLM_API_KEY" \
  -d '{
    "prompt": "Return JSON describing the project daedalus.",
    "schema": {
      "name": "string",
      "purpose": "string",
      "risks": ["string"]
    }
  }'
```

### POST /v1/summarise

```bash
curl http://127.0.0.1:8787/v1/summarise \
  -H "content-type: application/json" \
  -H "x-daedalus-api-key: $DAEDALUS_LLM_API_KEY" \
  -d '{
    "text": "Daedalus is an internal system that should call the LLM gateway instead of Ollama directly.",
    "maxWords": 50
  }'
```

### POST /v1/extract-evidence

```bash
curl http://127.0.0.1:8787/v1/extract-evidence \
  -H "content-type: application/json" \
  -H "x-daedalus-api-key: $DAEDALUS_LLM_API_KEY" \
  -d '{
    "question": "What evidence supports the gateway security model?",
    "text": "Raw Ollama is private on Tailscale. Apps authenticate to the gateway with x-daedalus-api-key. The gateway forwards approved requests to Ollama."
  }'
```

## systemd

Copy `systemd/daedalus-llm-gateway.service` to `/etc/systemd/system/daedalus-llm-gateway.service`.

Create `/etc/daedalus-llm-gateway.env`:

```bash
DAEDALUS_LLM_API_KEY=replace-with-a-long-random-secret
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=llama3.2:3b
HOST=0.0.0.0
PORT=8787
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now daedalus-llm-gateway
sudo systemctl status daedalus-llm-gateway
```

Firewall `8787` so only Tailscale/LAN clients can reach the gateway. Keep Ollama `11434` private to `daedalus-ai`.

Example UFW policy, adjusting the LAN CIDR if needed:

```bash
sudo ufw deny 8787/tcp
sudo ufw allow in on tailscale0 to any port 8787 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 8787 proto tcp
sudo ufw deny 11434/tcp
```

## Tests

```bash
npm test
```
