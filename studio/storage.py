"""SQLite persistence, isolated by a browser-specific local identity."""
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def identifier():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS resumes (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS resume_owner ON resumes(owner);
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS session_owner ON sessions(owner);
                CREATE TABLE IF NOT EXISTS requests (
                    owner TEXT, request_id TEXT, result TEXT,
                    PRIMARY KEY(owner, request_id));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, table, item_id, owner):
        assert table in ('resumes', 'sessions')
        with self.connect() as db:
            row = db.execute(f'SELECT payload FROM {table} WHERE id=? AND owner=?', (item_id, owner)).fetchone()
        if not row:
            raise KeyError('记录不存在或不属于当前浏览器。')
        return json.loads(row['payload'])

    def list(self, table, owner):
        assert table in ('resumes', 'sessions')
        with self.connect() as db:
            rows = db.execute(f'SELECT payload FROM {table} WHERE owner=? ORDER BY updated_at DESC', (owner,)).fetchall()
        return [json.loads(r['payload']) for r in rows]

    def put(self, table, value, owner):
        assert table in ('resumes', 'sessions')
        value['updated_at'] = now()
        with self.lock, self.connect() as db:
            existing = db.execute(f'SELECT owner FROM {table} WHERE id=?', (value['id'],)).fetchone()
            if existing and existing['owner'] != owner:
                raise KeyError('无权修改此记录。')
            db.execute(f'''INSERT INTO {table} VALUES (?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at, payload=excluded.payload''',
                       (value['id'], owner, value['created_at'], value['updated_at'], json.dumps(value, ensure_ascii=False)))
        return value

    def put_with_request(self, value, owner, request_id):
        """Persist the answer and idempotent response in one transaction."""
        value['updated_at'] = now()
        encoded = json.dumps(value, ensure_ascii=False)
        with self.lock, self.connect() as db:
            result = db.execute('UPDATE sessions SET payload=?,updated_at=? WHERE id=? AND owner=?',
                                (encoded, value['updated_at'], value['id'], owner))
            if result.rowcount != 1:
                raise KeyError('练习不存在。')
            if request_id:
                db.execute('INSERT OR REPLACE INTO requests VALUES(?,?,?)', (owner, request_id, encoded))
                db.execute('DELETE FROM requests WHERE owner=? AND rowid NOT IN '
                           '(SELECT rowid FROM requests WHERE owner=? ORDER BY rowid DESC LIMIT 100)', (owner, owner))
        return value

    def cached(self, owner, request_id):
        if not request_id:
            return None
        with self.connect() as db:
            row = db.execute('SELECT result FROM requests WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
        return json.loads(row['result']) if row else None

    def delete(self, table, item_id, owner):
        assert table in ('resumes', 'sessions')
        with self.lock, self.connect() as db:
            db.execute(f'DELETE FROM {table} WHERE id=? AND owner=?', (item_id, owner))
            if table == 'sessions':
                # Cached responses contain answers and must follow deletion.
                db.execute('DELETE FROM requests WHERE owner=?', (owner,))

    def weak_points(self, owner):
        totals = {}
        for session in self.list('sessions', owner)[:20]:
            for q in session['questions']:
                for dim in (q.get('result') or {}).get('dimensions', []):
                    totals.setdefault(dim['key'], []).append(dim['score'])
        labels = {'structure': '交代背景、任务和结果', 'depth': '解释决策依据和验证过程',
                  'expression': '组织清晰的回答结构', 'evidence': '补充真实且可核对的结果证据'}
        return [{'key': k, 'label': labels[k], 'average': round(sum(v)/len(v), 1)}
                for k, v in sorted(totals.items(), key=lambda p: sum(p[1])/len(p[1])) if sum(v)/len(v) < 17][:3]


def summarize(session):
    results = [q['result'] for q in session['questions'] if q.get('result')]
    return {k: session[k] for k in ['id', 'created_at', 'updated_at', 'role', 'resume_name', 'status', 'current_index']} | {
        'question_count': len(session['questions']), 'answered': len(results),
        'skipped': sum(q['stage'] == 'skipped' for q in session['questions']),
        'average': round(sum(r['total'] for r in results)/len(results), 1) if results else None,
        'engine': session['engine']}
