"""Ingest share files synced by iCloud into the local capture queue."""
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import select
import sys
import tempfile
import time
from urllib.parse import urlsplit

from capture import get_platform, has_visual_result, share_url, web_share_url


XHS_SHARE_SUFFIX = re.compile(
    r'(?:存下这段话[，,]\s*去\s*【小红书】\s*速览笔记'
    r'|把内容复制好[，,]\s*打开【小红书】即可看到笔记详情'
    r'|复制这段文字[，,]\s*打开【小红书】一键直达笔记'
    r'|把口令拷走[，,]\s*打开【小红书】查看详情'
    r'|直达【小红书】看看这篇分享'
    r'|戳【小红书】围观这篇内容'
    r'|把文本复制好[，,]\s*进入【小红书】即可浏览全文'
    r'|复制文本后进入【小红书】[，,]\s*直接查看笔记'
    r'|这篇笔记在【小红书】等你来读'
    r'|先复制再进入【小红书】[，,]\s*笔记内容马上出现)[~～。!！]*')


def split_share_note(value):
    lines = value.strip().splitlines()
    for index, line in enumerate(lines):
        try:
            url = share_url(line)
        except ValueError:
            continue
        if get_platform(url) == '小红书':
            suffix = line.partition(url)[2].strip()
            if suffix and not XHS_SHARE_SUFFIX.fullmatch(suffix):
                return value.strip(), ''
        return '\n'.join(lines[:index + 1]), '\n'.join(lines[index + 1:]).strip()
    return value.strip(), ''


def read_share(value):
    if value.startswith('灵感分享 v1\n'):
        _, _, fields = value.partition('\n')
        intent, separator, share = fields.rpartition('\n---分享链接---\n')
        if not separator:
            raise ValueError('分享文件还没有完整同步。')
        try:
            is_xhs = get_platform(share_url(share)) == '小红书'
        except ValueError:
            is_xhs = False
        if is_xhs:
            share, appended = split_share_note(share)
            intent = '\n\n'.join(part for part in (intent.strip(), appended) if part)
        return share.strip(), intent.strip()
    return split_share_note(value)


def has_saved_reference(body, intent):
    return (f'\n## 我想怎么用\n\n{intent}\n\n' in body
            and has_visual_result(body, intent))


def saved_section(body, heading):
    _, found, section = body.partition(f'\n## {heading}\n\n')
    if not found:
        return ''
    section = re.split(r'(?m)^## |^<!-- inspiration-reference:', section, maxsplit=1)[0]
    return '\n'.join(line for line in section.splitlines()
                     if line.strip() and not line.lstrip().startswith(('>', '#', '<!--'))).strip()


def archive_completed_share(path, content, digest, share, intent, status, archive):
    if not status or status['status'] != 'finished':
        return
    url = share_url(share)
    platform = get_platform(url)
    prefix, _, suffix = share.partition(url)
    default_xhs = platform == '小红书' and len(share.splitlines()) == 1 and (
        not suffix.strip() or XHS_SHARE_SUFFIX.fullmatch(suffix.strip()))
    default_bili = platform == 'B 站' and not suffix.strip() and re.fullmatch(
        r'【[^\n]+[-－–]哔哩哔哩】', prefix.strip())
    default_douyin = platform == '抖音' and re.fullmatch(
        r'\d+\.\d+\s+复制打开抖音[，,]\s*看看【[^】]+】[^\n]*',
        prefix.strip()) and re.fullmatch(r'[A-Za-z0-9@./:$ %_-]*', suffix.strip())
    if share != url and not any((default_xhs, default_bili, default_douyin)):
        return
    raw_name = status['message'].split(' ', 1)[-1].split(' · ', 1)[0]
    if Path(raw_name).name != raw_name or not raw_name.endswith('.md'):
        return
    note = path.parent.parent / '视频灵感' / raw_name
    body = note.read_text(encoding='utf-8-sig')
    header = body.split('---\n', 2)
    if len(header) != 3 or header[0]:
        return
    fields = set(header[1].splitlines())
    source = json.dumps(url, ensure_ascii=False)
    verified = json.dumps(status.get('video_source') or url, ensure_ascii=False)
    original_links = {f'来源: {source}', f'原分享链接: {source}'}
    image_digest = status.get('image_result_digest')
    if image_digest:
        _, marker, result = header[2].partition('\n## 发布文案\n')
        if (not original_links.intersection(fields) or '内容类型: "图文"' not in fields
                or not marker or sha256((marker[1:] + result).encode()).hexdigest() != image_digest):
            return
    elif (not (original_links | {f'来源: {verified}'}).intersection(fields)
          or not saved_section(header[2], '视频口播全文')):
        return
    if intent and not has_saved_reference(body, intent):
        return
    original = path.read_bytes()
    if original.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n').strip() != content:
        return
    archive.mkdir(parents=True, exist_ok=True)
    target = archive / f'{digest}-{path.name}'
    with tempfile.TemporaryDirectory(dir=archive) as staging:
        backup = Path(staging) / 'share'
        with backup.open('wb') as file:
            file.write(original)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(backup, target)
        except FileExistsError:
            if target.read_bytes() != original:
                return
    if path.read_bytes() == original:
        path.unlink()


def scan(directory, jobs):
    incomplete = False
    files = [*directory.glob('*.txt'), *directory.glob('*.md')]
    for path in sorted(files):
        try:
            if not path.is_file():
                continue
            info = path.stat()
            if info.st_size > 15000:
                continue
            if time.time_ns() - info.st_mtime_ns < 500_000_000:
                incomplete = True
                continue
            content = path.read_text(encoding='utf-8-sig').strip()
            after = path.stat()
            if (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                incomplete = True
                continue
            share, intent = read_share(content)
            web_share_url(share)
            dedup_key = None
            video = None
            try:
                video = urlsplit(share_url(share))
            except ValueError:
                pass
            else:
                if video.hostname in ('v.douyin.com', 'www.douyin.com') and (
                        video.hostname == 'v.douyin.com' or re.fullmatch(r'/video/\d+/?', video.path)):
                    url = video._replace(query='', fragment='').geturl().rstrip('/')
                    dedup_key = 'icloud_video_' + sha256(f'{url}\n{intent}'.encode()).hexdigest()
            digest = sha256(content.encode()).hexdigest()
            namespace = 'icloud_visual_' if intent and not content.startswith('灵感分享 v1\n') else 'icloud_'
            if video is not None and get_platform(video.geturl()) == '小红书':
                namespace = 'icloud_xhs_media_v2_' + namespace
            if (intent and namespace.startswith('icloud_xhs_media_v2_')
                    and content.startswith('灵感分享 v1\n')
                    and share != content.rsplit('\n---分享链接---\n', 1)[-1].strip()):
                namespace = 'icloud_multiline_' + namespace
            job = jobs.submit((share, '', intent, False), namespace + digest, dedup_key)
            if video is not None:
                archive_completed_share(path, content, digest, share, intent, jobs.status(job),
                                        jobs.database.parent / 'archived-mobile-shares')
        except (OSError, ValueError):
            incomplete = True
    return incomplete


def watch_files(directory, queue, watched):
    paths = {directory, *directory.glob('*.md'), *directory.glob('*.txt')}
    identities = {}
    for path in paths:
        try:
            info = path.stat()
            identities[path] = (info.st_dev, info.st_ino)
        except OSError:
            continue
    for path, (descriptor, identity) in list(watched.items()):
        if identities.get(path) != identity:
            os.close(descriptor)
            del watched[path]
    for path, identity in identities.items():
        if path in watched:
            continue
        try:
            descriptor = os.open(path, getattr(os, 'O_EVTONLY', os.O_RDONLY))
        except OSError:
            continue
        try:
            queue.control([select.kevent(
                descriptor, filter=select.KQ_FILTER_VNODE, flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                fflags=select.KQ_NOTE_WRITE | select.KQ_NOTE_EXTEND | select.KQ_NOTE_ATTRIB
                | select.KQ_NOTE_RENAME | select.KQ_NOTE_DELETE | select.KQ_NOTE_REVOKE,
            )], 0)
        except OSError:
            os.close(descriptor)
            continue
        watched[path] = descriptor, identity


def watch_changes(directory, jobs):
    read_fd, write_fd = os.pipe()
    os.set_blocking(read_fd, False)
    os.set_blocking(write_fd, False)
    watched = {}

    def notify_finished():
        try:
            os.write(write_fd, b'\0')
        except OSError:
            pass  # A notification is already pending, or the watcher closed.

    try:
        with closing(select.kqueue()) as queue:
            queue.control([select.kevent(read_fd, filter=select.KQ_FILTER_READ,
                                        flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR)], 0)
            jobs.on_finished = notify_finished
            retries = 0
            while True:
                os.listdir(directory)
                watch_files(directory, queue, watched)
                incomplete = scan(directory, jobs)
                # iCloud can replace files without delivering a local vnode notification.
                timeout = 60
                if directory not in watched:
                    timeout = 2
                elif incomplete and retries < 6:
                    timeout = 2 ** retries
                    retries += 1
                events = queue.control(None, 64, timeout)
                if any(event.ident == read_fd for event in events):
                    try:
                        while os.read(read_fd, 4096):
                            pass
                    except BlockingIOError:
                        pass
                if any(event.filter == select.KQ_FILTER_VNODE for event in events):
                    retries = 0
                    # Give iCloud time to finish writing or replacing a note.
                    time.sleep(0.4)
    finally:
        jobs.on_finished = None
        for descriptor, _ in watched.values():
            os.close(descriptor)
        os.close(read_fd)
        os.close(write_fd)


def watch_inbox(directory: Path, jobs):
    last_error = None
    while True:
        try:
            # pathlib.glob may silently hide permission errors on macOS.
            os.listdir(directory)
            ready_file = os.environ.get('CAPTURE_INBOX_READY_FILE')
            if ready_file:
                Path(ready_file).write_text(str(os.getpid()))
            print(f'收件箱就绪：{directory}', file=sys.stderr, flush=True)
            if hasattr(select, 'kqueue'):
                watch_changes(directory, jobs)
            else:
                while True:
                    scan(directory, jobs)
                    time.sleep(20)
        except OSError as error:
            if str(error) != last_error:
                print(f'收件箱暂不可用，将重试：{error}', file=sys.stderr, flush=True)
                last_error = str(error)
            time.sleep(20)
