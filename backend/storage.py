"""Small SQLite repository. Learner revisions and source versions are append-only."""
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import uuid

TABLES = ('packs','exercises','sources','sessions','attempts','events','jobs','settings','imports','observations')

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid.uuid4())

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory/'lab.sqlite3'
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS packs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS exercises(id TEXT PRIMARY KEY, pack_id TEXT NOT NULL REFERENCES packs(id), payload TEXT NOT NULL, answer TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, source_key TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(source_key, hash));
            CREATE VIRTUAL TABLE IF NOT EXISTS source_search USING fts5(id UNINDEXED, title, body);
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, exercise_id TEXT NOT NULL REFERENCES exercises(id), text TEXT NOT NULL DEFAULT '', outline TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), parent_id TEXT REFERENCES attempts(id), text TEXT NOT NULL, hash TEXT NOT NULL, created TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE, payload TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), kind TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES attempts(id), kind TEXT NOT NULL, status TEXT NOT NULL, request_key TEXT UNIQUE NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL, result TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS settings(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), skill TEXT NOT NULL, result TEXT NOT NULL, due TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL);
            PRAGMA user_version=1;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def rows(self, sql, args=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def execute(self, sql, args=()):
        with self.connect() as db:
            db.execute(sql, args)

    def event(self, session_id, kind, payload=None):
        self.execute('INSERT INTO events VALUES(?,?,?,?,?)', (uid(),session_id,kind,now(),dump(payload or {})))

    def setting(self, name, default=None):
        row = self.one('SELECT payload FROM settings WHERE id=?',(name,))
        return json.loads(row['payload']) if row else default

    def set_setting(self, name, value):
        self.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(name,dump(value)))

    def snapshot(self):
        """A single read transaction keeps tables mutually consistent."""
        with self.connect() as db:
            db.execute('BEGIN')
            tables = {name:[dict(r) for r in db.execute(f'SELECT * FROM {name}')] for name in TABLES}
        # Tokens are environment-owned and never enter the store.
        payload = {'schema':'awl.backup.v1','created':now(),'tables':tables}
        payload['checksum'] = digest(dump(tables))
        return payload

    def restore(self, backup):
        validate_backup(backup)
        # Validate using a fresh SQLite database before changing the active store.
        temp = self.directory/('restore-'+uid())
        candidate = Store(temp)
        with candidate.connect() as db:
            for name in reversed(TABLES):
                db.execute(f'DELETE FROM {name}')
            for name in TABLES:
                columns = [r['name'] for r in db.execute(f'PRAGMA table_info({name})')]
                for row in backup['tables'][name]:
                    if set(row) != set(columns):
                        raise ValueError(f'Invalid columns in {name}.')
                    db.execute(f'INSERT INTO {name} ({",".join(columns)}) VALUES({",".join("?" for _ in columns)})',[row[k] for k in columns])
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Backup has broken record references.')
            for row in db.execute('SELECT id,payload FROM sources').fetchall():
                p=json.loads(row['payload'])
                db.execute('INSERT INTO source_search VALUES(?,?,?)',(row['id'],p['title'],p['brief']))
            db.execute("UPDATE jobs SET status='interrupted', error='Restored job; request a new review.' WHERE status IN ('queued','running')")
        safety = self.snapshot()
        before = self.directory/('before-restore-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        before.write_text(dump(safety))
        with candidate.connect() as src, self.connect() as dst:
            src.backup(dst)
        return {'restored':True,'safety_backup':str(before),'attempts':len(backup['tables']['attempts'])}

def validate_backup(backup):
    if backup.get('schema') != 'awl.backup.v1' or set(backup.get('tables',{})) != set(TABLES):
        raise ValueError('Unsupported or incomplete backup.')
    if backup.get('checksum') != digest(dump(backup['tables'])):
        raise ValueError('Backup checksum does not match.')
    if any(not isinstance(rows,list) or len(rows)>100000 for rows in backup['tables'].values()):
        raise ValueError('Invalid backup record collection.')
