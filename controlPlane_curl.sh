#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${ATLAS_CONFIG_PATH:-$SCRIPT_DIR/config.json}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found." >&2
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Atlas configuration file not found: $CONFIG_PATH" >&2
  exit 1
fi

config_values="$({
  uv run python - "$CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
try:
    config = json.loads(config_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"Unable to read Atlas configuration: {error}")

if not isinstance(config, dict):
    raise SystemExit("Atlas configuration must be a JSON object.")

public_key = str(config.get("ATLAS_PUBLIC_KEY", "")).strip()
private_key = str(config.get("ATLAS_PRIVATE_KEY", "")).strip()
api_version = str(config.get("ATLAS_API_VERSION", "latest")).strip()
if not public_key or not private_key:
    raise SystemExit("Missing ATLAS_PUBLIC_KEY or ATLAS_PRIVATE_KEY in config.json.")

if api_version.lower() in {"latest", "auto"}:
    api_version = "2025-03-12"

print(public_key)
print(private_key)
print(api_version)
PY
} )"

line_number=0
while IFS= read -r value; do
  line_number=$((line_number + 1))
  case "$line_number" in
    1) ATLAS_PUBLIC_KEY="$value" ;;
    2) ATLAS_PRIVATE_KEY="$value" ;;
    3) ATLAS_API_VERSION="$value" ;;
  esac
done <<< "$config_values"

curl --user "$ATLAS_PUBLIC_KEY:$ATLAS_PRIVATE_KEY" \
  --digest --include \
  --header "Accept: application/vnd.atlas.$ATLAS_API_VERSION+json" \
  --request GET "https://cloud.mongodb.com/api/atlas/v2/unauth/controlPlaneIPAddresses?pretty=true"