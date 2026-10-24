# План-табель WFM · сервер ЛВС (3.31)
# Данные (канон, SQLite, бэкапы, журнал, сигналы, чат) — в /app/data через том;
# код сервера и OCR-ассеты остаются в образе и томом НЕ перекрываются.
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY server ./server
COPY node_modules ./node_modules
COPY План-табель-WFM-3.3*.html ./
ENV PT_PORT=8787 \
    PT_DATA=/app/data \
    PT_CANON=/app/data/canon.json \
    PT_HIST_DIR=/app/data/hist \
    PT_AUDIT=/app/data/audit.jsonl \
    PT_SIG_FILE=/app/data/sigs.json \
    PT_CHAT_FILE=/app/data/chat.json \
    PT_BACKUP_DIR=/app/data/backups \
    PT_OCR_DIR=/app/server/ocr
# PT_DB=/app/data/canon.db и PT_CANON_KEY задаются через compose/.env
EXPOSE 8787
VOLUME ["/app/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PT_PORT||8787)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node","server/sync-server.mjs"]
