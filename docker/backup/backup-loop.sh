
#!/bin/bash
set -Eeuo pipefail

export TZ=Europe/Istanbul

echo "BTM PostgreSQL otomatik yedekleme aktif."
echo "Planlanan saat: 02:00 (Europe/Istanbul)"

while true; do
    TODAY=$(date +%Y-%m-%d)
    CURRENT_TIME=$(date +%H%M)
    MARKER="/backups/.backup-$TODAY.done"

    if [[ "$CURRENT_TIME" -ge 0200 && ! -f "$MARKER" ]]; then
        if /bin/bash /scripts/backup-once.sh; then
            touch "$MARKER"
            find /backups \
                -maxdepth 1 \
                -name '.backup-*.done' \
                -mtime +35 \
                -delete
        else
            echo "Yedekleme basarisiz; yeniden denenecek."
        fi
    fi

    sleep 60
done
