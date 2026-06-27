#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

git fetch origin
git reset --hard origin/main

npm ci
npm run deploy

curl -fsS https://petllama.martinbibb.workers.dev/health
printf '\n'
