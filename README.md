# Daedalus-ai

## daedalus-llm-gateway

Fastify API gateway for private Ollama access on the Daedalus network.

Apps should call this gateway only. Do not expose raw Ollama publicly.

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
