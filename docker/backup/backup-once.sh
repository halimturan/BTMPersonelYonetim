
#!/bin/bash
set -Eeuo pipefail

BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

BACKUP_FILE="$BACKUP_DIR/btm_$DATE.dump"
TEMP_FILE="${BACKUP_FILE}.partial"

mkdir -p "$BACKUP_DIR"

cleanup() {
    rm -f "$TEMP_FILE"
}

trap cleanup EXIT

echo "PostgreSQL yedekleme basladi: $(date)"

pg_dump \
    --format=custom \
    --no-owner \
    --no-acl \
    --file="$TEMP_FILE"

test -s "$TEMP_FILE"
pg_restore --list "$TEMP_FILE" > /dev/null

mv "$TEMP_FILE" "$BACKUP_FILE"

trap - EXIT

echo "Yedek olusturuldu: $BACKUP_FILE"

RETENTION="${BACKUP_RETENTION_DAYS:-30}"

if [[ "$RETENTION" =~ ^[1-9][0-9]*$ ]]; then
    find "$BACKUP_DIR" \
        -maxdepth 1 \
        -type f \
        -name 'btm_*.dump' \
        -mtime +"$RETENTION" \
        -delete
fi

echo "Yedekleme tamamlandi: $(date)"
