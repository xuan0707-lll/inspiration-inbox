"""Durable jobs for the local Chrome capture service."""
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import Event, Thread
import time
from uuid import uuid4


class CaptureJobs:
    def __init__(self, database: Path, save):
        self.database = database
        self.save = save
        self.wake = Event()
        self.on_finished = None
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL, message TEXT NOT NULL)""")
            columns = {column[1] for column in connection.execute('PRAGMA table_info(jobs)')}
            connection.execute('CREATE TABLE IF NOT EXISTS submissions '
                               '(request_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, digest TEXT NOT NULL)')
            if 'result' not in columns:
                connection.execute('ALTER TABLE jobs ADD COLUMN result TEXT')
            if 'attempts' not in columns:
                connection.execute('ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
                connection.execute('ALTER TABLE jobs ADD COLUMN retry_at INTEGER NOT NULL DEFAULT 0')
        Thread(target=self.work, daemon=True, name='capture-jobs').start()

    def connect(self):
        return sqlite3.connect(self.database, timeout=5)

    def submit(self, payload, request_id=None, dedup_key=None):
        job = uuid4().hex
        serialized = json.dumps(payload, ensure_ascii=False)
        with closing(self.connect()) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            if request_id:
                digest = sha256(serialized.encode()).hexdigest()
                previous = connection.execute(
                    'SELECT job_id, digest FROM submissions WHERE request_id = ?',
                    (request_id,)).fetchone()
                if previous:
                    if previous[1] != digest:
                        raise ValueError('这次保存编号已经对应另一条分享。')
                    if dedup_key:
                        connection.execute('INSERT OR IGNORE INTO submissions VALUES (?, ?, ?)',
                                           (dedup_key, previous[0], digest))
                    return previous[0]
                if dedup_key:
                    previous = connection.execute(
                        'SELECT job_id FROM submissions WHERE request_id = ?', (dedup_key,)).fetchone()
                    if previous:
                        connection.execute('INSERT INTO submissions VALUES (?, ?, ?)',
                                           (request_id, previous[0], digest))
                        return previous[0]
                    connection.execute('INSERT INTO submissions VALUES (?, ?, ?)', (dedup_key, job, digest))
                connection.execute('INSERT INTO submissions VALUES (?, ?, ?)',
                                   (request_id, job, digest))
            connection.execute('INSERT INTO jobs (id, payload, status, message) VALUES (?, ?, ?, ?)',
                               (job, serialized, 'queued', '已接收，正在后台处理。'))
        self.wake.set()
        return job

    def status(self, job):
        with closing(self.connect()) as connection:
            row = connection.execute('SELECT status, message, result FROM jobs WHERE id = ?', (job,)).fetchone()
        if not row:
            return None
        status, message, result = row
        return {'status': status, 'message': message, **(json.loads(result) if result else {})}

    def work(self):
        while True:
            self.wake.clear()
            with closing(self.connect()) as connection:
                row = connection.execute(
                    "SELECT id, payload, attempts FROM jobs WHERE "
                    "(status = 'queued' OR status = 'retrying') AND retry_at <= ? "
                    "ORDER BY retry_at, rowid LIMIT 1", (int(time.time()),)).fetchone()
                next_retry = connection.execute(
                    "SELECT MIN(retry_at) FROM jobs WHERE status = 'retrying'").fetchone()[0]
            if not row:
                self.wake.wait(None if next_retry is None else max(1, next_retry - time.time()))
                continue
            job, payload, attempts = row
            result = None
            try:
                outcome = self.save(*json.loads(payload))
                status, message = outcome[:2]
                if len(outcome) == 3:
                    result = json.dumps(outcome[2], ensure_ascii=False)
            except Exception:
                message, status = '写入失败，请保留原链接后重试。', 'failed'
            retry_at = 0
            if status in ('needs_media', 'needs_visual') and attempts < 3:
                retry_at = int(time.time()) + 300 * 2 ** attempts
                status = 'retrying'
                message += ' 稍后会自动重试。'
            else:
                payload = '[]'
            with closing(self.connect()) as connection, connection:
                connection.execute('UPDATE jobs SET status = ?, message = ?, payload = ?, '
                                   'attempts = ?, retry_at = ?, result = ? WHERE id = ?',
                                   (status, message, payload, attempts + 1, retry_at, result, job))
            if status == 'finished' and self.on_finished:
                self.on_finished()
