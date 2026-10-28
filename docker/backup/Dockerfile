FROM postgres:17

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY backup-once.sh /scripts/backup-once.sh
COPY backup-loop.sh /scripts/backup-loop.sh
