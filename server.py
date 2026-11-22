"""Authenticated processing endpoint. The caller writes returned notes into iCloud."""
from base64 import b64encode
from tempfile import NamedTemporaryFile, TemporaryDirectory
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
from threading import Thread
from urllib.parse import unquote

from urllib.parse import parse_qs, urlsplit

from capture import VAULT, VISUAL_RANGE, executable, get_platform, has_visual_result, note_filename, process_local_media, process_share, requested_visual_range, save_reference_clip, share_url, web_share_url, write_capture_note
from watch import watch_forever
from jobs import CaptureJobs
from inbox import watch_inbox


def simple_note(url, title, intent, pending=False, followed=False):
    fields = [
        f'来源: {json.dumps(url, ensure_ascii=False)}',
        f'标题: {json.dumps(title, ensure_ascii=False)}',
    ]
    if followed:
        fields.append('入口: "特别关注"')
    note = '\n'.join(['---', *fields, '---', '', '# ' + title, ''])
    if intent.strip():
        note += '\n## 我想怎么用\n\n' + intent.strip() + '\n'
    if pending:
        note += '\n## 状态\n\n暂未提取口播。原链接已保留。\n'
    return note


def shared_title(share, url):
    # Mobile apps often share the caption and URL as a single text item.
    prefix = share.split(url, 1)[0].strip()
    bilibili = re.search(r'【(.+?)[-－–]哔哩哔哩】', prefix)
    douyin = re.search(r'看看\s*【[^】]+的作品】\s*(.+)', prefix, re.DOTALL)
    if bilibili:
        prefix = bilibili.group(1)
    elif douyin:
        prefix = douyin.group(1)
    elif not prefix or re.search(r'复制打开抖音|复制此链接', prefix):
        return ''
    return ' '.join(prefix.split())[:120]


def capture_note(share, title, intent, followed, reuse=False):
    if not share.strip():
        raise ValueError('分享内容为空。')
    try:
        url = share_url(share)
    except ValueError:
        if followed:
            raise ValueError('特别关注需要受支持的视频链接。')
        url = web_share_url(share)
        folder = '网页灵感'
    else:
        try:
            reuse_dir = VAULT / '视频灵感' if reuse and not followed else None
            source, info, heading, note = process_share(
                url, intent, followed, allow_partial=True, reuse_dir=reuse_dir)
        except (OSError, ValueError, subprocess.SubprocessError):
            folder = '视频待处理'
        else:
            folder = '视频待处理' if info.get('transcript_pending') else (
                '特别关注' if followed else '视频灵感')
            return source, info, heading, note, folder
    title = ' '.join(title.split())[:200] or shared_title(share, url) or urlsplit(url).hostname
    return url, {}, title, simple_note(url, title, intent, folder == '视频待处理', followed), folder


def save_tab(share, title, intent, followed, keep_clip=False, recording=None, page=None):
    if recording:
        return save_recording(share, title, intent, followed, keep_clip, Path(recording), page)
    source, info, heading, note, folder = capture_note(share, title, intent, followed, reuse=not keep_clip)
    if folder == '视频待处理':
        write_capture_note(VAULT / folder, heading, info, source, note, intent)
        return 'needs_media', '已存链接到「视频待处理」，暂未拿到完整口播。'
    outcome = persist_note(source, info, heading, note, folder, intent, keep_clip)
    if info.get('image_result_digest'):
        return (*outcome, {'image_result_digest': info['image_result_digest']})
    if (intent and folder == '视频灵感' and not info.get('reference_append')
            and not has_visual_result(note, intent)):
        return 'needs_visual', outcome[1] + ' · 口播和备注已保存，画面分析未完成。'
    return (*outcome, {'video_source': source}) if get_platform(source) else outcome


def save_recording(share, title, intent, followed, keep_clip, recording, page):
    folder = '特别关注' if followed else '视频灵感'
    try:
        ffmpeg = executable('ffmpeg')
        if not ffmpeg:
            raise ValueError('缺少 ffmpeg。')
        with TemporaryDirectory() as directory:
            media = Path(directory) / 'recording.webm'
            # Chrome's MediaRecorder streams usually omit the total duration from the header.
            subprocess.run(
                [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-protocol_whitelist', 'file',
                 '-f', 'matroska', '-i', str(recording), '-map', '0:v:0', '-map', '0:a:0',
                 '-c', 'copy', str(media)], check=True, timeout=45, capture_output=True)
            source, info, heading, note = process_local_media(share, intent, followed, media, title, page)
            outcome = persist_note(source, info, heading, note, folder, intent, keep_clip, media)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 'failed', f'录制暂未整理成功。本机原文件在 recordings/{recording.name}。'
    try:
        recording.unlink(missing_ok=True)
    except OSError:
        return outcome[0], outcome[1] + ' · 临时录制文件仍保存在本机。'
    return outcome


def persist_note(source, info, heading, note, folder, intent, keep_clip, media=None):
    try:
        (path, created), detail = write_capture_note(
            VAULT / folder, heading, info, source, note, intent, keep_clip, media)
    except ValueError as error:
        (path, created), _ = write_capture_note(VAULT / folder, heading, info, source, note, intent)
        detail = str(error)
    action = '已保存 ' if created else ('已补充画面参考 ' if info.get('reference_append') else '已存在 ')
    message = action + path.name
    return 'finished', message + (f' · {detail}' if detail else '')


def capture_result(share, title, intent, followed, keep_clip=False):
    source, info, heading, note, folder = capture_note(share, title, intent, followed)
    name, _ = note_filename(heading, info, source)
    result = {'name': name, 'markdown': note, 'folder': folder}
    if keep_clip and folder != '视频待处理':
        try:
            focus = requested_visual_range(intent, info.get('duration') or 0)
            if not focus:
                raise ValueError('缺少片段时间。')
            with TemporaryDirectory() as temporary:
                clip = save_reference_clip(info, Path(temporary), focus)
                if clip.stat().st_size > 6_000_000:
                    raise ValueError('片段过大。')
                result['clip'] = {'name': clip.name, 'base64': b64encode(clip.read_bytes()).decode('ascii')}
                result['markdown'] += f'\n## 画面参考片段\n\n![[画面片段/{clip.name}]]\n'
        except (OSError, ValueError, subprocess.SubprocessError):
            result['clip_warning'] = '画面片段未能生成，正文已保留。'
    return result


def prepare_mobile(share, title, intent, followed, keep_clip=False):
    result = capture_result(share, title, intent, followed, keep_clip)
    if result['folder'] == '视频待处理':
        return 'needs_media', '已保留链接和说明，暂未拿到完整口播。', result
    return 'finished', '笔记已整理，可以保存到 Obsidian。', result


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(12)

    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, scope=None):
        supplied = self.headers.get('Authorization', '')
        scoped_key = getattr(self.server, scope + '_secret', '') if scope else ''
        keys = (self.server.secret, scoped_key) if scoped_key else (self.server.secret,)
        if any(hmac.compare_digest(supplied.encode(), ('Bearer ' + key).encode()) for key in keys):
            return True
        self.reply(401, {'error': '处理端凭证不正确。'})
        return False

    def do_GET(self):
        target = urlsplit(self.path)
        if target.path.startswith(('/jobs/', '/mobile-jobs/')):
            mobile = target.path.startswith('/mobile-jobs/')
            if not self.authorized('mobile' if mobile else None):
                return
            resource = 'mobile_jobs' if mobile else 'jobs'
            jobs = getattr(self.server, resource, None)
            result = jobs.status(target.path.rsplit('/', 1)[-1]) if jobs else None
            self.reply(200 if result else 404, result or {'error': '找不到这次保存记录。'})
            return
        if target.path != '/followed':
            self.reply(404, {'error': '地址不正确。'})
            return
        if not self.authorized('followed'):
            return
        export = os.environ.get('CAPTURE_FOLLOWED_EXPORT')
        if not export:
            self.reply(503, {'error': '特别关注尚未配置。'})
            return
        query = parse_qs(target.query)
        try:
            after = int(query.get('after', ['0'])[0])
            after_name = query.get('name', [''])[0]
            if after < 0 or len(after_name) > 255:
                raise ValueError
        except ValueError:
            self.reply(400, {'error': '进度标记不正确。'})
            return
        try:
            found = []
            for path in Path(export).glob('*.md'):
                if not path.is_file():
                    continue
                key = (path.stat().st_mtime_ns // 1000, path.name)
                if key > (after, after_name):
                    found.append((key, path))
            batch = sorted(found)[:15]
            notes = [{'name': path.name, 'markdown': path.read_text(encoding='utf-8')}
                     for _, path in batch]
        except OSError:
            self.reply(503, {'error': '暂时无法读取已整理的笔记。'})
            return
        stamp, name = batch[-1][0] if batch else (after, after_name)
        self.reply(200, {'folder': '特别关注', 'notes': notes, 'more': len(found) > len(batch),
                         'cursor': {'after': str(stamp), 'name': name}})

    def submit_recording(self):
        jobs = getattr(self.server, 'jobs', None)
        if not jobs:
            self.reply(403, {'error': '录制仅支持本机入库。'})
            return
        try:
            if self.headers.get_content_type() != 'video/webm':
                raise ValueError('录制文件需要是 WebM。')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 128_000_000:
                raise ValueError('录制为空或超过 128 MB。')
            metadata = self.headers.get('Capture-Metadata', '')
            if not 0 < len(metadata) <= 18000:
                raise ValueError('录制缺少视频信息，或说明过长。')
            data = json.loads(unquote(metadata))
            if not isinstance(data, dict):
                raise ValueError('录制信息格式不正确。')
            text_fields = {key: data.get(key, '') for key in ('share', 'title', 'intent', 'uploader', 'description')}
            if not all(isinstance(value, str) for value in text_fields.values()):
                raise ValueError('录制信息应为文本。')
            share = share_url(text_fields.pop('share'))
            title = text_fields.pop('title')[:200]
            intent = text_fields.pop('intent')[:2000]
            duration = data.get('original_duration')
            if type(duration) in (int, float) and 0 < duration <= 86400:
                text_fields['original_duration'] = duration
            if not title.strip():
                title = '浏览器播放录制'
            followed, clip = (data.get('followed', False), data.get('keep_clip', False))
            if type(followed) is not bool or type(clip) is not bool:
                raise ValueError('录制设置格式不正确。')
            directory = jobs.database.parent / 'recordings'
            directory.mkdir(mode=0o700, exist_ok=True)
            with NamedTemporaryFile(dir=directory, suffix='.webm', delete=False) as stream:
                path = Path(stream.name)
                try:
                    remaining = size
                    while remaining:
                        chunk = self.rfile.read(min(remaining, 256 * 1024))
                        if not chunk:
                            raise ValueError('录制文件没有传完。')
                        stream.write(chunk)
                        remaining -= len(chunk)
                    stream.flush()
                    job = jobs.submit((share, title, intent, followed, clip, str(path), text_fields))
                except Exception:
                    path.unlink(missing_ok=True)
                    raise
        except ValueError as error:
            self.reply(422, {'error': str(error)})
            return
        except OSError:
            self.reply(503, {'error': '录制文件暂时无法保存。'})
            return
        self.reply(202, {'job': job, 'message': '录制已交给本机转写。'})

    def do_POST(self):
        if self.path == '/save-recording':
            if self.authorized():
                self.submit_recording()
            return
        if self.path not in ('/capture', '/save-tab', '/capture-async'):
            self.reply(404, {'error': '地址不正确。'})
            return
        if not self.authorized('mobile' if self.path == '/capture-async' else None):
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16000:
                raise ValueError('请求内容为空或过长。')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('请求应为 JSON 对象。')
            share, intent = data.get('share'), data.get('intent', '')
            followed = data.get('followed', False)
            if not isinstance(share, str) or not isinstance(intent, str) or type(followed) is not bool:
                raise ValueError('请传入分享链接、用途文字和特别关注标记。')
            title = data.get('title', '')
            if not isinstance(title, str):
                raise ValueError('标题应为文本。')
            local_save = self.path == '/save-tab'
            if local_save and os.environ.get('CAPTURE_LOCAL_SAVE') != '1':
                self.reply(403, {'error': '这个处理端未开启本机入库。'})
                return
            keep_clip = data.get('keep_clip', False)
            if type(keep_clip) is not bool:
                raise ValueError('短片选项必须为布尔值。')
            if keep_clip:
                share_url(share)
                if not VISUAL_RANGE.search(intent):
                    raise ValueError('请在用途里写明片段时间，例如 00:40–00:45。')
            if local_save or self.path == '/capture-async':
                resource = 'jobs' if local_save else 'mobile_jobs'
                jobs = getattr(self.server, resource, None)
                if jobs is None:
                    self.reply(503, {'error': '后台任务服务未启动。'})
                    return
                request_id = self.headers.get('Idempotency-Key')
                if request_id is not None and not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', request_id):
                    raise ValueError('保存编号格式不正确。')
                payload = (share, title, intent, followed)
                if keep_clip:
                    payload += (True,)
                job = jobs.submit(payload, request_id)
                self.reply(202, {'job': job, 'message': '已接收，正在后台处理。'})
                return
            result = capture_result(share, title, intent, followed, keep_clip)
            self.reply(200, {**result, 'status': 'pending' if result['folder'] == '视频待处理' else 'ready'})
        except ValueError as error:
            self.reply(422, {'error': str(error)})
        except (OSError, subprocess.SubprocessError):
            self.reply(503, {'error': '暂时无法处理或保存，请保留原链接。'})


if __name__ == '__main__':
    secret = os.environ.get('CAPTURE_SECRET', '')
    if len(secret) < 24:
        raise SystemExit('请设置至少 24 字符的 CAPTURE_SECRET。')
    server = HTTPServer((os.environ.get('BIND_HOST', '127.0.0.1'), int(os.environ.get('PORT', '18787'))), Handler)
    server.secret = secret
    server.followed_secret = os.environ.get('CAPTURE_FOLLOWED_SECRET', '')
    server.mobile_secret = os.environ.get('CAPTURE_MOBILE_SECRET', '')
    if any(0 < len(key) < 24 for key in (server.followed_secret, server.mobile_secret)):
        raise SystemExit('特别关注和手机收集的专用密钥至少需要 24 个字符。')
    if os.environ.get('CAPTURE_LOCAL_SAVE') == '1':
        default_database = Path.home() / '.local/state/inspiration-tool/capture.sqlite'
        database = Path(os.environ.get('CAPTURE_JOBS_STATE', str(default_database)))
        server.jobs = CaptureJobs(database, save_tab)
        inbox = os.environ.get('CAPTURE_ICLOUD_INBOX')
        if inbox:
            Thread(target=watch_inbox, args=(Path(inbox), server.jobs),
                   name='icloud-inbox', daemon=True).start()
    mobile_database = os.environ.get('CAPTURE_MOBILE_JOBS_STATE')
    if mobile_database:
        server.mobile_jobs = CaptureJobs(Path(mobile_database), prepare_mobile)
    feeds = os.environ.get('CAPTURE_FEEDS')
    if feeds:
        export = os.environ.get('CAPTURE_FOLLOWED_EXPORT')
        state = os.environ.get('CAPTURE_WATCH_STATE')
        interval = int(os.environ.get('CAPTURE_WATCH_INTERVAL', '120'))
        if not export or not state or interval < 60:
            raise SystemExit('自动检测需要设置导出目录、状态文件和至少 60 秒的轮询间隔。')
        Thread(target=watch_forever, args=(Path(feeds), Path(state), Path(export), interval),
               name='creator-updates', daemon=True).start()
    server.serve_forever()
