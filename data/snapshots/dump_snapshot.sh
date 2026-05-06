#!/usr/bin/env bash
# Dump analyzed articles, analyses, and seat_predictions to a compressed SQL file.
# Run from the repo root: bash data/snapshots/dump_snapshot.sh
set -euo pipefail

CONTAINER="tracking_votes-postgres-1"
DB="johor_elections"
USER="johor"
SNAPSHOT="data/snapshots/snapshot.sql.gz"

echo "Preparing snapshot table..."

# Create a real table (not temp — needs to persist for the pg_dump call)
docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -c "
  DROP TABLE IF EXISTS articles_snapshot;
  CREATE TABLE articles_snapshot (LIKE articles INCLUDING ALL);
  INSERT INTO articles_snapshot
    SELECT * FROM articles WHERE id IN (SELECT DISTINCT article_id FROM analyses);
" > /dev/null

echo "Dumping..."

# --data-only: only COPY blocks, no DDL. Rename snapshot table to articles in output.
docker exec "$CONTAINER" pg_dump -U "$USER" "$DB" \
  --no-owner --no-acl \
  --data-only \
  --table=articles_snapshot \
  --table=analyses \
  --table=seat_predictions \
  | sed 's/public\.articles_snapshot/public.articles/g; s/articles_snapshot/articles/g' \
  | gzip > "$SNAPSHOT"

docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -c \
  "DROP TABLE IF EXISTS articles_snapshot;" > /dev/null

ROWS=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM articles WHERE id IN (SELECT DISTINCT article_id FROM analyses);" | tr -d ' ')
ANALYSES=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM analyses;" | tr -d ' ')
PREDS=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM seat_predictions;" | tr -d ' ')

echo "Done: $SNAPSHOT"
echo "  articles (analyzed only): $ROWS"
echo "  analyses:                 $ANALYSES"
echo "  seat_predictions:         $PREDS"
echo "  file size:                $(du -sh "$SNAPSHOT" | cut -f1)"
