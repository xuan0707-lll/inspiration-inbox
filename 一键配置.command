#!/bin/bash
set -eu
cd "$(dirname "$0")"
src="$PWD"
app="$HOME/Library/Application Support/InspirationInbox"
state="$HOME/.local/state/inspiration-inbox"
vault="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/灵感与素材"
label=local.inspiration-inbox
agent="$HOME/Library/LaunchAgents/$label.plist"
domain="gui/$(id -u)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
[ "$(uname -sm)" = "Darwin arm64" ] || { echo '首版需要 Apple 芯片 Mac。'; exit 1; }
if ! xcode-select -p >/dev/null 2>&1; then
    xcode-select --install || true
    echo '请在系统弹窗完成 Apple 命令行工具安装，然后再次双击本文件。图文识字需要其中的 Swift。'
    exit 1
fi
if [ ! -d "$vault" ]; then
    echo '请先在 iPhone 的 Obsidian 创建「灵感与素材」库，开启 Store in iCloud，再等 Mac 的 iCloud 云盘出现 Obsidian 文件夹。'
    exit 1
fi
if /usr/sbin/lsof -nP -iTCP:18787 -sTCP:LISTEN >/dev/null 2>&1 && ! launchctl print "$domain/$label" >/dev/null 2>&1; then
    echo '18787 端口已有其他后台运行。请先退出占用端口的旧服务，再安装。'
    exit 1
fi
mkdir -p "$app/.tools" "$state" "$HOME/Library/LaunchAgents" "$vault/手机分享收件箱"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
if ! command -v uv >/dev/null; then
    echo '正在从 Astral 官方安装 uv，用于准备 Python 和本机模型。'
    curl -fsSL --retry 2 https://astral.sh/uv/install.sh -o "$work/uv-install.sh"
    UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="$HOME/.local/bin" sh "$work/uv-install.sh"
fi
toolrunner=$(command -v uv)
ln -sfn "$toolrunner" "$app/.tools/uv"
uv python install 3.13
uv venv --allow-existing --python 3.13 "$app/.tools/media"
py="$app/.tools/media/bin/python"
uv pip install --python "$py" yt-dlp imageio-ffmpeg
ln -sfn "$py" "$app/.tools/python3"
ln -sfn "$app/.tools/media/bin/yt-dlp" "$app/.tools/yt-dlp"
ln -sfn "$("$py" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" "$app/.tools/ffmpeg"
prepare_model() {
    echo "正在准备 $2，第一次需联网下载模型，下载中断后可重新运行。"
    uv tool run --python 3.13 --from "$1" python -c 'from huggingface_hub import snapshot_download; import sys; snapshot_download(sys.argv[1],ignore_patterns=["*.md",".gitattributes"])' "$2"
}
prepare_model mlx-whisper mlx-community/whisper-large-v3-turbo
prepare_model mlx-lm mlx-community/Qwen3-1.7B-4bit
prepare_model mlx-vlm mlx-community/Qwen3-VL-2B-Instruct-4bit
for item in capture.py server.py watch.py inbox.py jobs.py describe_frames.py read_frames.swift summarize.py transcribe_mlx.py start-local.sh; do
    cp "$src/$item" "$app/$item"
done
bundle="$app/灵感入库后台.app"
build="$work/灵感入库后台.app"
mkdir -p "$build/Contents/MacOS"
swiftc "$src/InboxLauncher.swift" -o "$build/Contents/MacOS/InboxLauncher"
"$py" - "$build/Contents/Info.plist" <<'PLIST'
import plistlib, sys
from pathlib import Path
Path(sys.argv[1]).write_bytes(plistlib.dumps(dict(
    CFBundleIdentifier='local.inspiration-inbox.launcher', CFBundleName='灵感入库后台',
    CFBundleExecutable='InboxLauncher', CFBundlePackageType='APPL', CFBundleVersion='1',
    LSUIElement=True)))
PLIST
codesign --force --sign - "$build"
ditto "$build" "$bundle"
codesign --verify "$bundle"
if [ ! -e "$state/creators.json" ]; then echo '[]' > "$state/creators.json"; fi
"$py" - "$app" "$state" "$agent" "$label" <<'PY'
import pathlib,plistlib,sys
app,state,agent,label=sys.argv[1:]
cfg=dict(Label=label,AssociatedBundleIdentifiers=['local.inspiration-inbox.launcher'],ProgramArguments=[app+'/灵感入库后台.app/Contents/MacOS/InboxLauncher'],RunAtLoad=True,KeepAlive=True,ThrottleInterval=20,EnvironmentVariables=dict(CAPTURE_LOCAL_STATE_DIR=state,CAPTURE_INBOX_READY_FILE=state+'/inbox-ready'),StandardOutPath=state+'/service.log',StandardErrorPath=state+'/errors.log')
p=pathlib.Path(agent)
tmp=p.with_suffix('.new')
tmp.write_bytes(plistlib.dumps(cfg))
tmp.replace(p)
PY
if launchctl print "$domain/$label" >/dev/null 2>&1; then launchctl bootout "$domain/$label"; fi
launchctl bootstrap "$domain" "$agent"
wait_for_inbox() {
    for attempt in {1..20}; do
        worker=$(cat "$state/inbox-ready" 2>/dev/null || true)
        if [[ "$worker" =~ ^[0-9]+$ ]] && /usr/sbin/lsof -a -p "$worker" -iTCP:18787 -sTCP:LISTEN >/dev/null 2>&1; then return 0; fi
        sleep 1
    done
    return 1
}
if ! wait_for_inbox; then
    echo '后台尚未读到收件箱。请在弹窗里选择 iCloud 中的「灵感与素材」文件夹。'
    open -n -W "$bundle" --args --authorize
    launchctl kickstart -k "$domain/$label"
    wait_for_inbox || { echo "后台未就绪，查看 $state/errors.log"; exit 1; }
fi
echo '后台已读取手机分享收件箱，下次登录会自动启动。正在打开快捷指令。'
open "$src/mobile/存到灵感库.shortcut"
echo '请按 README 的 iPhone 首次配置添加控制中心按钮。'
