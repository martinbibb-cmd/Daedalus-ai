# Manual Ripper

Service for Daedalus manual ingestion and evidence-backed question answering. It can run on the VM or as a NAS/Unraid container.

This is RAG, not model training. PDFs are stored on the configured manual storage path, extracted page by page, and answered from structured evidence/facts.

The current catalogue extraction lane focuses on boiler/manual-derived van stock
because those are the first reviewed manuals available. The service boundary is
broader: manuals are supporting evidence for the whole Place Twin, not a
heating-only product surface.

## Storage

Default storage path:

```text
/srv/daedalus/manuals/
  originals/
  extracted/
  facts/
  indexes/
  assets/
  metadata.sqlite
```

NAS-backed storage can be enabled without changing code:

```bash
AI_SUPPORT_ROOT=/mnt/user/ai-support
MANUAL_RIPPER_STORAGE_ROOT=/mnt/user/ai-support/manuals
MANUAL_RIPPER_RAW_DIR=/mnt/user/ai-support/manuals/raw
MANUAL_RIPPER_EXTRACTED_DIR=/mnt/user/ai-support/manuals/extracted
MANUAL_RIPPER_FACTS_DIR=/mnt/user/ai-support/manuals/facts
MANUAL_RIPPER_INDEXES_DIR=/mnt/user/ai-support/manuals/indexes
MANUAL_RIPPER_ASSETS_DIR=/mnt/user/ai-support/manuals/assets
AI_REGRESSIONS_DIR=/mnt/user/ai-support/regressions
DEPOT_NOTES_EXAMPLES_DIR=/mnt/user/ai-support/depot-notes/examples
```

`facts/` stores structured manual facts separately from the page/index files so answer synthesis can prefer exact table facts before raw PDF text.

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
MANUAL_RIPPER_RAW_DIR=/srv/daedalus/manuals/originals
MANUAL_RIPPER_EXTRACTED_DIR=/srv/daedalus/manuals/extracted
MANUAL_RIPPER_FACTS_DIR=/srv/daedalus/manuals/facts
MANUAL_RIPPER_INDEXES_DIR=/srv/daedalus/manuals/indexes
MANUAL_RIPPER_ASSETS_DIR=/srv/daedalus/manuals/assets
DAEDALUS_LLM_GATEWAY_URL=<DAEDALUS_LLM_GATEWAY_URL>
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

## Offline catalogue extraction

The lab also includes a deterministic batch pipeline for turning reviewed
manual text into Capture van-stock catalogue candidates. This is deliberately
not LLM extraction and does not auto-promote technical truth.

Input:

- PDF, text or Markdown manuals under a controlled inbox such as
  `/srv/daedalus/manuals/inbox`.
- PDFs require `pdftotext` from `poppler-utils`.

Candidate output:

```text
manual-derived-van-stock.candidates.json
manual-ripper-report.json
```

Reviewed output for Capture:

```text
manual-derived-van-stock.json
manual-derived-van-stock.approval.json
```

Run the deterministic candidate extractor:

```bash
python3 bin/manual_catalogue_ripper.py \
  --input /srv/daedalus/manuals/inbox \
  --output /srv/daedalus/manuals/output/manual-derived-van-stock.candidates.json \
  --report /srv/daedalus/manuals/output/manual-ripper-report.json
```

Promote only after human review:

```bash
python3 bin/promote_reviewed_catalogue.py \
  --candidates /srv/daedalus/manuals/output/manual-derived-van-stock.candidates.json \
  --output /srv/daedalus/manuals/reviewed/manual-derived-van-stock.json \
  --approval /srv/daedalus/manuals/reviewed/manual-derived-van-stock.approval.json \
  --approved-by "reviewer name"
```

The promoted catalogue shape matches Capture's bundled van-stock fixture and
must remain reviewable back to manual evidence. Unreviewed candidates are not
authoritative stock data.

## systemd

```bash
sudo cp systemd/daedalus-manual-ripper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daedalus-manual-ripper
sudo systemctl status daedalus-manual-ripper
```

Keep the service private, ideally behind Cloudflare Tunnel or local network access.

## Unraid / NAS Container

The container stores all persistent data under `/mnt/user/ai-support` on the host.

```bash
cd manual-ripper
docker compose -f docker-compose.unraid.yml up -d --build
```

Required Unraid path mapping:

```text
/mnt/user/ai-support  ->  /mnt/user/ai-support
```

Expose port `8791` only on the LAN or through a controlled Cloudflare Tunnel route.

Point the Worker at the NAS-hosted service:

```toml
MANUAL_RIPPER_BASE_URL = "https://your-private-manual-ripper.example"
```

If using a direct LAN URL for testing:

```toml
MANUAL_RIPPER_BASE_URL = "http://<unraid-ip>:8791"
```

Health check:

```bash
curl http://<unraid-ip>:8791/health
```
