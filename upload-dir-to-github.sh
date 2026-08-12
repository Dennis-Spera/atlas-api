#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./upload-dir-to-github.sh
#   ./upload-dir-to-github.sh --branch main --message "Sync playbook-atlas-api directory"
#   ./upload-dir-to-github.sh --repo https://github.com/Dennis-Spera/atlas-api --target-dir playbook-atlas-api

REPO_URL="https://github.com/Dennis-Spera/atlas-api"
BRANCH="main"
TARGET_DIR="."
COMMIT_MESSAGE="Sync directory contents"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --repo <url>          Git repository URL (default: $REPO_URL)
  --branch <name>       Target branch to push (default: $BRANCH)
  --target-dir <path>   Directory path inside repo (default: $TARGET_DIR)
  --message <text>      Commit message (default: $COMMIT_MESSAGE)
  -h, --help            Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO_URL="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    --message)
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -d "$SCRIPT_DIR" ]]; then
  echo "Source directory not found: $SCRIPT_DIR" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required but was not found." >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

REPO_DIR="$WORKDIR/repo"
echo "Cloning $REPO_URL (branch: $BRANCH)..."
if ! git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO_DIR"; then
  echo "Branch '$BRANCH' was not found during clone. Trying default branch and creating local branch..."
  git clone "$REPO_URL" "$REPO_DIR"
  pushd "$REPO_DIR" >/dev/null
  git checkout -B "$BRANCH"
  popd >/dev/null
fi

DEST_DIR="$REPO_DIR/$TARGET_DIR"
mkdir -p "$DEST_DIR"

echo "Syncing files from $SCRIPT_DIR to $DEST_DIR..."
rsync -a --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude 'config.json' \
  --exclude '*.log' \
  --exclude '*.log.*' \
  "$SCRIPT_DIR/" "$DEST_DIR/"

pushd "$REPO_DIR" >/dev/null

git add -A "$TARGET_DIR"
git reset --quiet HEAD -- "$TARGET_DIR/config.json" "$TARGET_DIR"/*.log "$TARGET_DIR"/*.log.* 2>/dev/null || true
if git diff --cached --quiet; then
  echo "No staged changes. Nothing to commit."
  exit 0
fi

git commit -m "$COMMIT_MESSAGE"
git push origin "$BRANCH"

popd >/dev/null

echo "Uploaded directory $SCRIPT_DIR to $REPO_URL on branch $BRANCH at path $TARGET_DIR"
