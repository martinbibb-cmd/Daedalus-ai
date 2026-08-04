# Manual Ripper

Service for Daedalus manual ingestion and evidence-backed question answering. The canonical Xeon runtime is on `daedalus-dev` (Tailscale `100.90.15.43`), not `daedalus-llm`. It can also run as a NAS/Unraid container.

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

Canonical Xeon layout:

```text
/srv/daedalus/apps/Daedalus-ai/manual-ripper  # Git source
/srv/daedalus/manual-ripper                   # installed runtime
/srv/daedalus/manuals                         # mutable manual storage
/srv/daedalus/regressions                     # deterministic regression data
/etc/daedalus-manual-ripper.env               # root-owned, mode 0600
```

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
HOST=127.0.0.1
PORT=8791
```

The safe default omits all gateway and external API variables. Do not add real keys unless a separate approved change explicitly enables evidence-backed answer generation. Deterministic extraction does not need them.

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

### Publish finalized results to NAS

The Xeon keeps SQLite, indexes and working files locally. After review, publish
only finalized outputs and their provenance to the NAS-backed immutable results
tree:

```bash
python3 bin/publish_reviewed_results.py
```

The command requires the reviewed catalogue and approval metadata, verifies the
NAS mount, writes checksums and source-commit provenance, and finalizes a new
UTC-named directory under:

```text
/mnt/daedalus-nas/Manuals/Results/manual-ripper/
```

It does not publish raw manuals, SQLite working state, indexes, credentials or
temporary files, and it never overwrites an earlier published run. Published
files are root-owned through the restricted NAS SSH identity and world-readable
but not world-writable, so Martin can inspect them while the immutable archive
cannot be edited through the normal NAS user account.

## systemd

```bash
sudo cp systemd/daedalus-manual-ripper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daedalus-manual-ripper
sudo systemctl status daedalus-manual-ripper
```

Keep the Xeon service bound to `127.0.0.1`. Reach it only through a private SSH/Tailscale hop; do not add a public tunnel or listener.

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
