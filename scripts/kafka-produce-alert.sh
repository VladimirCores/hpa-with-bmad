#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALERT_LOG="${SCRIPT_DIR}/../output/alerts/alert-log.ndjson"

usage() {
    echo "Usage: $0 [--dry-run] <alert_json>"
    echo ""
    echo "Produce alert signals to Kafka topics."
    echo "  --dry-run    Print alert to stdout instead of persisting"
    echo ""
    echo "Example:"
    echo "  $0 --dry-run '{\"alert_id\":\"019...\",\"severity\":\"info\",...}'"
    exit 1
}

DRY_RUN=false
ALERT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            ALERT="$1"
            shift
            ;;
    esac
done

if [[ -z "$ALERT" ]]; then
    usage
fi

if $DRY_RUN; then
    echo "$ALERT"
    exit 0
fi

mkdir -p "$(dirname "$ALERT_LOG")" 2>/dev/null || true
echo "$ALERT" >> "$ALERT_LOG"