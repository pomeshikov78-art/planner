#!/usr/bin/env bash
# Установка сервера План-табель WFM как службы systemd (автоподнятие после сбоев и перезагрузок).
# Использование: sudo bash server/install-service.sh [порт] [каталог-источник]
set -euo pipefail
PORT="${1:-8787}"
SRC="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
DEST=/opt/plan-tabel
UNIT=/etc/systemd/system/plan-tabel.service

if [[ $EUID -ne 0 ]]; then echo "Нужен root: sudo bash $0 [порт]"; exit 1; fi
if ! command -v node >/dev/null; then echo "node не найден в PATH — установите Node.js 18+"; exit 1; fi
NODE_BIN=$(command -v node)

echo "→ копирую $SRC в $DEST"
mkdir -p "$DEST"
cp -r "$SRC"/server "$SRC"/*.html "$SRC"/package.json "$SRC"/package-lock.json "$DEST"/ 2>/dev/null || true
cd "$DEST"
# зависимости сервера — только ws
if [[ ! -d node_modules/ws ]]; then
  echo "→ ставлю зависимость ws"
  npm i --omit=dev --no-audit --no-fund ws >/dev/null 2>&1 || npm i --no-audit --no-fund ws
fi

echo "→ пользователь службы"
id -u plan-tabel >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin plan-tabel || true
chown -R plan-tabel:plan-tabel "$DEST"

echo "→ окружение (порт $PORT)"
cat > "$DEST/server/plan-tabel.env" <<EOF
PT_PORT=$PORT
PT_HOST=0.0.0.0
PT_CANON=$DEST/server/plan-tabel-canon.json
PT_HIST_DIR=$DEST/server/plan-tabel-hist
PT_AUDIT=$DEST/server/plan-tabel-server-audit.jsonl
PT_SIG_FILE=$DEST/server/plan-tabel-sigs.json
PT_CHAT_FILE=$DEST/server/plan-tabel-chat.json
PT_OCR_DIR=$DEST/server/ocr
# PT_USERS_FILE=$DEST/server/users.json
# PT_QUOTA=editor:300
# PT_REPLICA_OF=ws://primary:$PORT
# PT_SHARED_SECRET=
# PT_DIGEST_CRON=08:30,17:00
EOF
chown plan-tabel:plan-tabel "$DEST/server/plan-tabel.env"

echo "→ unit-файл"
sed -e "s#ExecStart=/usr/bin/node#ExecStart=$NODE_BIN#" "$SRC/server/plan-tabel.service" > "$UNIT"
systemctl daemon-reload
systemctl enable plan-tabel.service >/dev/null 2>&1 || true
systemctl restart plan-tabel.service
sleep 1
systemctl --no-pager --lines=5 status plan-tabel.service || true
echo
echo "Готово. Сервер: http://localhost:$PORT/ · статус: /status · админ: /admin"
echo "Журнал: journalctl -u plan-tabel -f"
