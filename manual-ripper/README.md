# Manual Ripper

Local VM service for boiler/heating manual ingestion and evidence-backed question answering.

This is RAG, not model training. PDFs are stored locally, extracted page by page, searched with keyword scoring, and only the retrieved evidence is sent to the Daedalus LLM Gateway for answer generation.

## Storage

Default storage path:

```text
/srv/daedalus/manuals/
  originals/
  extracted/
  indexes/
  metadata.sqlite
```

## Install

```bash
cd manual-ripper
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
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

Do not commit real keys.

## Run

```bash
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8791
```

## API

- `GET /health`
- `GET /manuals`
- `POST /manuals/upload`
- `GET /manuals/{id}`
- `POST /manuals/{id}/extract`
- `POST /manuals/{id}/query`
- `POST /manuals/search`

## systemd

```bash
sudo cp systemd/daedalus-manual-ripper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daedalus-manual-ripper
sudo systemctl status daedalus-manual-ripper
```

Keep the service private, ideally behind Cloudflare Tunnel or local network access.
