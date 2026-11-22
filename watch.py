"""Poll configured creator sources and keep completed notes in an export directory."""
import argparse
import json
import re
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from capture import get_bytes, get_platform, share_url, process_share, write_note

DOUYIN_MOBILE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) '
                  'AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1',
}


def video_key(url):
    parts = urlsplit(url)
    host = parts.hostname or ''
    path = parts.path.rstrip('/')
    if host == 'www.bilibili.com' and re.fullmatch(r'/video/(?:BV[0-9A-Za-z]+|av[0-9]+)', path):
        # The part selector identifies different media within a multi-part upload.
        part = next((value for key, value in parse_qsl(parts.query) if key == 'p'), '1')
        query = urlencode({'p': part}) if part.isdigit() and int(part) > 1 else ''
        return urlunsplit(('https', host, path, query, ''))
    if host == 'www.douyin.com' and re.fullmatch(r'/video/[0-9]+', path):
        return urlunsplit(('https', host, path, '', ''))
    if host == 'www.xiaohongshu.com':
        match = re.fullmatch(r'/(?:explore|discovery/item)/([a-f0-9]+)', path)
        if match:
            # Keep the complete original share URL for extraction, including its access parameters.
            return f'https://www.xiaohongshu.com/explore/{match[1]}'
    return parts._replace(fragment='').geturl()


def feed_links(content):
    root = ElementTree.fromstring(content)
    kind = root.tag.rsplit('}', 1)[-1]
    if kind == 'rss':
        if root.find('{*}channel') is None:
            raise ValueError('RSS 更新源缺少频道。')
        entries = root.findall('{*}channel/{*}item')
    elif kind == 'RDF':
        entries = root.findall('{*}item')
    elif kind == 'feed':
        entries = root.findall('{*}entry')
    else:
        raise ValueError('更新源需要返回 RSS 或 Atom。')
    for entry in entries:
        for link in entry.findall('{*}link'):
            if link.get('rel', 'alternate') != 'alternate':
                continue
            try:
                url = share_url(link.get('href') or link.text or '')
            except ValueError:
                continue
            yield url
            break
        else:
            yield None


def douyin_creator_links(url, fetch):
    parts = urlsplit(url)
    match = re.fullmatch(r'/m/user/([0-9]{1,24})/?', parts.path)
    if parts.netloc != 'jingxuan.douyin.com' or not match or parts.query or parts.fragment:
        raise ValueError('请填写抖音精选公开作者页的数字编号地址。')
    document = fetch(url, headers=DOUYIN_MOBILE_HEADERS).decode('utf-8')
    marker = re.search(r'window\._SSR_DATA\s*=\s*', document)
    if not marker:
        raise ValueError('抖音精选没有返回作者作品列表。')
    state, _ = json.JSONDecoder().raw_decode(document[marker.end():])
    try:
        page = state['data']['storeState']['user-page']
        creator = page['userInfo']['result']
        videos = page['videoList']['result']
        if (str(creator.get('id')) != match[1] or creator.get('notFound')
                or page['videoList'].get('error') or not isinstance(videos, list)):
            raise ValueError('抖音精选未返回对应作者的有效作品列表。')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('抖音精选作品列表的结构有变化。') from error
    links = {}
    for video in videos:
        if not isinstance(video, dict):
            continue
        video_id = str(video.get('gid', ''))
        timestamp = str(video.get('publishTime', ''))
        if re.fullmatch(r'[0-9]{15,25}', video_id) and timestamp.isdigit():
            links[video_id] = int(timestamp)
    if not links and (videos or creator.get('videoTotalCount')):
        raise ValueError('抖音精选暂未返回可用的作品链接。')
    return [f'https://www.douyin.com/video/{video_id}'
            for video_id in sorted(links, key=lambda item: (links[item], item), reverse=True)]


def observed_links(feed, fetch):
    url = feed['url']
    if urlsplit(url).scheme != 'https':
        raise ValueError('更新源需要 HTTPS。')
    if feed.get('kind') == 'douyin-creator':
        return douyin_creator_links(url, fetch)
    entries = list(feed_links(fetch(url)))
    links = list(dict.fromkeys(link for link in entries if link))
    profile = feed.get('profile')
    if profile:
        # A feed may contain links outside the expected platform, such as sponsor links.
        platform = get_platform(profile)
        if not platform:
            raise ValueError('博主主页需要是受支持的平台地址。')
        links = [link for link in links if get_platform(link) == platform]
    if entries and not links:
        raise ValueError('更新源当前没有可用的视频链接。')
    return links


def poll(database, feeds, output, fetch=get_bytes, process=process_share, now=None):
    now = int(time.time()) if now is None else now
    database.executescript("""
        CREATE TABLE IF NOT EXISTS sources (url TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS video (
            url TEXT PRIMARY KEY, state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, retry_at INTEGER NOT NULL DEFAULT 0
        );
    """)
    failures = []
    for feed in feeds:
        url = feed['url']
        try:
            links = observed_links(feed, fetch)
        except (ValueError, OSError, ElementTree.ParseError) as error:
            failures.append(f"{feed.get('name') or urlsplit(url).hostname}：{error}")
            continue
        with database:
            seen = database.execute('SELECT 1 FROM sources WHERE url = ?', (url,)).fetchone()
            state = 'pending' if seen or feed.get('include_existing') else 'baseline'
            known = {video_key(row[0]): row for row in database.execute('SELECT url, state FROM video')}
            for link in reversed(links):
                key = video_key(link)
                previous = known.get(key)
                if previous:
                    old_url, old_state = previous
                    if (old_state == 'pending' and old_url != link
                            and urlsplit(link).hostname == 'www.xiaohongshu.com'
                            and 'xsec_token' in dict(parse_qsl(urlsplit(link).query))):
                        database.execute('UPDATE OR IGNORE video SET url = ? WHERE url = ?', (link, old_url))
                        known[key] = (link, old_state)
                    continue
                database.execute('INSERT INTO video(url, state) VALUES (?, ?)', (link, state))
                known[key] = (link, state)
            database.execute('INSERT OR IGNORE INTO sources VALUES (?)', (url,))
    saved = []
    # Hold the writer lock for one item so concurrent runs won't transcribe it twice.
    while True:
        database.execute('BEGIN IMMEDIATE')
        with database:
            row = database.execute(
                "SELECT url, attempts FROM video WHERE state = 'pending' AND retry_at <= ? "
                "ORDER BY retry_at, rowid LIMIT 1", (now,)).fetchone()
            if row is None:
                break
            url, attempts = row
            try:
                source, info, title, note = process(url, '', True)
                path, created = write_note(output, title, info, source, note)
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                retry_at = now + min(3600, 120 * 2 ** min(attempts, 5))
                database.execute('UPDATE video SET attempts = ?, retry_at = ? WHERE url = ?',
                                 (attempts + 1, retry_at, url))
                failures.append(str(error))
            else:
                database.execute("UPDATE video SET state = 'ready' WHERE url = ?", (url,))
                if created:
                    saved.append(path)
    return saved, failures


def run_cycle(feeds, state, output):
    state.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(state, timeout=2) as database:
        saved, failures = poll(database, json.loads(feeds.read_text(encoding='utf-8')), output)
    for path in saved:
        print(f'已整理：{path.name}', flush=True)
    for error in failures:
        print(f'本轮未完成：{error}', flush=True)
    return bool(failures)


def watch_forever(feeds, state, output, interval):
    while True:
        started = time.monotonic()
        try:
            run_cycle(feeds, state, output)
        except (OSError, ValueError, KeyError, sqlite3.Error) as error:
            print(f'特别关注暂未运行：{error}', flush=True)
        time.sleep(max(1, interval - (time.monotonic() - started)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feeds', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--interval', type=int, help='持续检查的间隔（秒）。省略时只检查一次。')
    args = parser.parse_args()
    if args.interval is not None:
        if args.interval < 60:
            parser.error('--interval 至少为 60 秒。')
        watch_forever(args.feeds, args.state, args.out, args.interval)
    raise SystemExit(run_cycle(args.feeds, args.state, args.out))


if __name__ == '__main__':
    main()
