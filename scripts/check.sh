#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
output_dir="${CHECK_OUTPUT_DIR:-docs/evidence/runtime}"
mkdir -p "$output_dir"

collect_logs() {
  docker compose ps -a > "$output_dir/compose-ps.txt" 2>&1 || true
  docker compose logs --no-color --tail=300 > "$output_dir/compose-logs.txt" 2>&1 || true
}

docker compose version | tee "$output_dir/compose-version.txt"
trap collect_logs EXIT
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 600 2>&1 | tee "$output_dir/compose-up.txt"
docker compose ps -a | tee "$output_dir/compose-ps.txt"
python3 scripts/verify.py "$@" --output "$output_dir/api-check.txt"
