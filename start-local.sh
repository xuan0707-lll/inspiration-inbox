#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PATH="$PWD/.tools:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export CAPTURE_VAULT="${CAPTURE_VAULT:-$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感与素材}"
state="${CAPTURE_LOCAL_STATE_DIR:-$HOME/.local/state/inspiration-tool}"
mkdir -p "$state"
export CAPTURE_SECRET
CAPTURE_SECRET=$(python3 - "$state/chrome-token" <<'PY'
import os
from pathlib import Path
import secrets
import sys
import tempfile

path = Path(sys.argv[1])
if not path.exists():
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as key:
            key.write(secrets.token_urlsafe(32) + '\n')
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        os.unlink(temporary)
if path.is_symlink() or path.stat().st_mode & 0o077:
    raise SystemExit('本机密钥文件需为仅当前用户可读写的普通文件。')
print(path.read_text().strip())
PY
)
# Enable the installed local model if its weights are already in the cache.
if [ -z "${LOCAL_TEXT_MODEL+x}" ] && [ "$(uname -s):$(uname -m)" = Darwin:arm64 ]; then
    model_root="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3-1.7B-4bit/snapshots"
    for weights in "$model_root/"*/model.safetensors; do
        if [ -s "$weights" ]; then
            export LOCAL_TEXT_MODEL=mlx-community/Qwen3-1.7B-4bit
            break
        fi
    done
fi
if [ -z "${LOCAL_VISION_MODEL+x}" ] && [ "$(uname -s):$(uname -m)" = Darwin:arm64 ]; then
    vision_root="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3-VL-2B-Instruct-4bit/snapshots"
    for weights in "$vision_root/"*/model.safetensors; do
        model_dir="${weights%/*}"
        if [ -s "$weights" ] && [ -s "$model_dir/preprocessor_config.json" ] &&
            [ -s "$model_dir/tokenizer.json" ]; then
            export LOCAL_VISION_MODEL=mlx-community/Qwen3-VL-2B-Instruct-4bit
            break
        fi
    done
fi
if [ "$(uname -s)" = Darwin ] && [ "${CAPTURE_DISABLE_ICLOUD_INBOX:-0}" != 1 ]; then
    CAPTURE_ICLOUD_INBOX="${CAPTURE_ICLOUD_INBOX:-$CAPTURE_VAULT/手机分享收件箱}"
    mkdir -p "$CAPTURE_ICLOUD_INBOX"
    export CAPTURE_ICLOUD_INBOX
fi
if [ -f "$state/creators.json" ]; then
    export CAPTURE_FEEDS="$state/creators.json"
    export CAPTURE_FOLLOWED_EXPORT="$CAPTURE_VAULT/特别关注"
    export CAPTURE_WATCH_STATE="$state/follow.sqlite"
fi
export CAPTURE_LOCAL_SAVE=1
export CAPTURE_JOBS_STATE="$state/capture.sqlite"
export BIND_HOST=127.0.0.1
export PORT="${PORT:-18787}"
exec python3 server.py
