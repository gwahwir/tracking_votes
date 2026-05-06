#!/usr/bin/env bash
# Restore articles, analyses, and seat_predictions from the latest snapshot.
# Run from the repo root: bash data/snapshots/restore_snapshot.sh
#
# WARNING: This will DELETE all existing rows in articles, analyses, and
# seat_predictions before loading the snapshot. Historical and demographic
# tables are not touched.
set -euo pipefail

CONTAINER="tracking_votes-postgres-1"
DB="johor_elections"
USER="johor"
SNAPSHOT="data/snapshots/snapshot.sql.gz"

if [ ! -f "$SNAPSHOT" ]; then
  echo "ERROR: $SNAPSHOT not found. Run data/snapshots/dump_snapshot.sh first."
  exit 1
fi

echo "Restoring from $SNAPSHOT..."
echo "  file size: $(du -sh "$SNAPSHOT" | cut -f1)"

docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -c "
  TRUNCATE analyses, seat_predictions, articles CASCADE;
"

zcat "$SNAPSHOT" | docker exec -i "$CONTAINER" psql -U "$USER" -d "$DB" \
  --set ON_ERROR_STOP=on

ROWS=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM articles;" | tr -d ' ')
ANALYSES=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM analyses;" | tr -d ' ')
PREDS=$(docker exec "$CONTAINER" psql -U "$USER" -d "$DB" -t -c \
  "SELECT COUNT(*) FROM seat_predictions;" | tr -d ' ')

echo "Done."
echo "  articles:         $ROWS"
echo "  analyses:         $ANALYSES"
echo "  seat_predictions: $PREDS"
