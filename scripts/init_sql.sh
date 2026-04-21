#!/bin/sh
set -e

RISINGWAVE_HOST="${RISINGWAVE_HOST:-risingwave}"
RISINGWAVE_PORT="${RISINGWAVE_PORT:-4566}"
RISINGWAVE_USER="${RISINGWAVE_USER:-root}"
RISINGWAVE_DB="${RISINGWAVE_DB:-dev}"

echo "=== RisingWave SQL Initialisation ==="
echo "Target: $RISINGWAVE_HOST:$RISINGWAVE_PORT/$RISINGWAVE_DB"

echo "Waiting for RisingWave to accept connections..."
RETRIES=30
until psql -h "$RISINGWAVE_HOST" -p "$RISINGWAVE_PORT" -U "$RISINGWAVE_USER" -d "$RISINGWAVE_DB" -c "SELECT 1" > /dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        echo "ERROR: RisingWave did not become ready in time."
        exit 1
    fi
    echo "  Not ready yet, retrying in 5s... ($RETRIES attempts left)"
    sleep 5
done
echo "RisingWave is ready."

for f in \
    /sql/01_sources.sql \
    /sql/02_staging.sql \
    /sql/03_fraud_signals.sql \
    /sql/04_risk_aggregations.sql \
    /sql/05_case_management.sql; do

    echo ""
    echo "--- Executing $f ---"
    psql -h "$RISINGWAVE_HOST" -p "$RISINGWAVE_PORT" -U "$RISINGWAVE_USER" -d "$RISINGWAVE_DB" \
        -v ON_ERROR_STOP=1 -f "$f"
    echo "--- Done: $f ---"
done

echo ""
echo "=== Verifying objects ==="

SOURCE_COUNT=$(psql -h "$RISINGWAVE_HOST" -p "$RISINGWAVE_PORT" -U "$RISINGWAVE_USER" -d "$RISINGWAVE_DB" \
    -t -c "SELECT COUNT(*) FROM rw_catalog.rw_sources;" | tr -d ' \n')
VIEW_COUNT=$(psql -h "$RISINGWAVE_HOST" -p "$RISINGWAVE_PORT" -U "$RISINGWAVE_USER" -d "$RISINGWAVE_DB" \
    -t -c "SELECT COUNT(*) FROM rw_catalog.rw_materialized_views;" | tr -d ' \n')

echo "Sources created  : $SOURCE_COUNT (expected 5)"
echo "Views created    : $VIEW_COUNT (expected 18)"

if [ "$SOURCE_COUNT" -lt 5 ]; then
    echo "ERROR: Expected 5 sources, found $SOURCE_COUNT"
    exit 1
fi

if [ "$VIEW_COUNT" -lt 18 ]; then
    echo "ERROR: Expected 18 materialized views, found $VIEW_COUNT"
    exit 1
fi

echo ""
echo "All SQL objects created successfully. Pipeline is ready."
