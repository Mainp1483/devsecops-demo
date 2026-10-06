#!/usr/bin/env bash
# Kiểm tra nhanh môi trường Ubuntu: ./doctor.sh
cd "$(dirname "$0")" || exit 1
ok()  { echo "  [OK]   $*"; }
bad() { echo "  [FAIL] $*"; }
[ -f .env.sonar ] && set -a && . ./.env.sonar && set +a
URL="${SONAR_HOST_URL:-http://localhost:9000}"

echo "== 1. Công cụ =="
for c in git python3 docker curl; do
  if command -v "$c" >/dev/null; then ok "$c: $($c --version 2>&1 | head -1)"; else bad "thiếu $c"; fi
done
python3 -c "import venv" 2>/dev/null && ok "python3-venv có sẵn" || bad "thiếu venv: sudo apt install python3-venv"

echo "== 2. Docker =="
if docker info >/dev/null 2>&1; then ok "docker daemon chạy, user dùng được"
else bad "docker không chạy hoặc user chưa trong group docker -> sudo systemctl start docker; sudo usermod -aG docker \$USER; đăng xuất/đăng nhập lại"; fi
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^sonarqube$'; then ok "container sonarqube đang chạy"
else bad "container sonarqube chưa chạy -> docker compose up -d ; xem log: docker compose logs --tail=50 sonarqube"; fi

echo "== 3. SonarQube ($URL) =="
ST=$(curl -s --max-time 5 "$URL/api/system/status")
echo "$ST" | grep -q '"status":"UP"' && ok "SonarQube status UP" || bad "chưa UP (trả về: ${ST:-không phản hồi}). STARTING = đợi thêm 1-2 phút"
if [ -n "$SONAR_TOKEN" ]; then
  curl -s --max-time 5 -u "$SONAR_TOKEN:" "$URL/api/authentication/validate" | grep -q '"valid":true' \
    && ok "token hợp lệ" || bad "token sai/hết hạn -> tạo lại ở My Account > Security"
  curl -s --max-time 5 -u "$SONAR_TOKEN:" "$URL/api/components/show?component=devsecops-demo" | grep -q '"key":"devsecops-demo"' \
    && ok "project devsecops-demo tồn tại" || bad "chưa có project key devsecops-demo (tạo ở UI hoặc chạy ./scan.sh lần đầu)"
else
  bad "chưa có SONAR_TOKEN (tạo .env.sonar từ .env.sonar.example)"
fi

echo "== 4. Git hook =="
[ "$(git config core.hooksPath)" = ".githooks" ] && ok "core.hooksPath = .githooks" || bad "chạy: git config core.hooksPath .githooks"
[ -x .githooks/post-merge ] && ok "post-merge có quyền thực thi" || bad "chạy: chmod +x .githooks/post-merge"
[ -f .sonar-scan.log ] && { echo "  --- 8 dòng cuối .sonar-scan.log ---"; tail -8 .sonar-scan.log; }

echo "== 5. App =="
[ -d venv ] && ok "có venv" || bad "chưa có venv: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
