#!/usr/bin/env bash
# Quét thủ công (Ubuntu). Debug: chạy `bash -x ./scan.sh`
cd "$(dirname "$0")" || exit 1
[ -f .env.sonar ] && set -a && . ./.env.sonar && set +a
: "${SONAR_HOST_URL:=http://localhost:9000}"
[ -z "$SONAR_TOKEN" ] && { echo "Thiếu SONAR_TOKEN (tạo .env.sonar)"; exit 1; }

docker run --rm --network host \
  -u "$(id -u):$(id -g)" \
  -e SONAR_HOST_URL="$SONAR_HOST_URL" \
  -e SONAR_TOKEN="$SONAR_TOKEN" \
  -v "$(pwd):/usr/src" \
  sonarsource/sonar-scanner-cli
