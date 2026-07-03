FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AI_SUPPORT_ROOT=/mnt/user/ai-support \
    MANUAL_RIPPER_STORAGE_ROOT=/mnt/user/ai-support/manuals \
    MANUAL_RIPPER_RAW_DIR=/mnt/user/ai-support/manuals/raw \
    MANUAL_RIPPER_EXTRACTED_DIR=/mnt/user/ai-support/manuals/extracted \
    MANUAL_RIPPER_FACTS_DIR=/mnt/user/ai-support/manuals/facts \
    MANUAL_RIPPER_INDEXES_DIR=/mnt/user/ai-support/manuals/indexes \
    MANUAL_RIPPER_ASSETS_DIR=/mnt/user/ai-support/manuals/assets \
    AI_REGRESSIONS_DIR=/mnt/user/ai-support/regressions \
    HOST=0.0.0.0 \
    PORT=8791

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8791

CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8791}"]
