#!/bin/bash
set -eu
state="$HOME/.local/state/inspiration-inbox"
[ -f "$state/creators.json" ] || { echo '请先完成「一键配置」。'; exit 1; }
read -r -p '粘贴抖音精选作者页链接（https://jingxuan.douyin.com/m/user/数字）：' creator
python3 - "$state/creators.json" "$creator" <<'PY'
import json,re,sys,tempfile,os,fcntl
from pathlib import Path
path=Path(sys.argv[1])
url=sys.argv[2].strip().rstrip('/')
if not re.fullmatch(r'https://jingxuan\.douyin\.com/m/user/[0-9]{1,24}',url):
    raise SystemExit('链接格式不符，请复制抖音精选的作者页。')
with path.with_suffix('.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    sources=json.loads(path.read_text())
    if not any(s['url']==url for s in sources):
        sources.append(dict(kind='douyin-creator',url=url))
        with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as f:
            json.dump(sources,f,indent=2)
        os.replace(f.name,path)
print('已关注。首次检查会记住现有作品，之后发现新作会自动入库。')
PY
