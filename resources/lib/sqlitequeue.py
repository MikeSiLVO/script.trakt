import os
import sqlite3
from json import loads, dumps

from time import sleep

import threading
from _thread import get_ident

import xbmcvfs
import xbmcaddon
import logging
from typing import Any, Iterator, Optional, Dict

logger = logging.getLogger(__name__)

__addon__ = xbmcaddon.Addon('script.trakt')

# code from http://flask.pocoo.org/snippets/88/ with some modifications
class SqliteQueue:

    _create = (
                'CREATE TABLE IF NOT EXISTS queue '
                '('
                '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
                '  item BLOB'
                ')'
                )
    _count = 'SELECT COUNT(*) FROM queue'
    _iterate = 'SELECT id, item FROM queue'
    _append = 'INSERT INTO queue (item) VALUES (?)'
    _write_lock = 'BEGIN IMMEDIATE'
    _get = (
            'SELECT id, item FROM queue '
            'ORDER BY id LIMIT 1'
            )
    _del = 'DELETE FROM queue WHERE id = ?'
    _peek = (
            'SELECT item FROM queue '
            'ORDER BY id LIMIT 1'
            )
    _purge = 'DELETE FROM queue'

    path: str
    _connection_cache: Dict[int, sqlite3.Connection]

    def __init__(self) -> None:
        self.path = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
        if not xbmcvfs.exists(self.path):
            logger.debug("Making path structure: %s" % repr(self.path))
            xbmcvfs.mkdir(self.path)
        self.path = os.path.join(self.path, 'queue.db')
        self._connection_cache = {}
        with self._get_conn() as conn:
            conn.execute(self._create)

    def __len__(self) -> int:
        with self._get_conn() as conn:
            executed = conn.execute(self._count).fetchone()[0]
        return executed

    def __iter__(self) -> Iterator[Any]:
        with self._get_conn() as conn:
            for _, obj_buffer in conn.execute(self._iterate):
                yield loads(obj_buffer)

    def _get_conn(self) -> sqlite3.Connection:
        tid = get_ident()
        # Evict connections from dead threads to prevent unbounded cache growth
        alive_tids = {t.ident for t in threading.enumerate()}
        stale_tids = [t for t in self._connection_cache if t not in alive_tids]
        for stale_tid in stale_tids:
            try:
                self._connection_cache[stale_tid].close()
            except Exception:
                pass
            del self._connection_cache[stale_tid]
        if tid not in self._connection_cache:
            self._connection_cache[tid] = sqlite3.Connection(self.path, timeout=60)
        return self._connection_cache[tid]

    def purge(self) -> None:
        with self._get_conn() as conn:
            conn.execute(self._purge)

    def append(self, obj: Any) -> None:
        obj_buffer = dumps(obj)
        with self._get_conn() as conn:
            conn.execute(self._append, (obj_buffer,))

    def get(self, sleep_wait: bool = True) -> Optional[Any]:
        keep_pooling = True
        wait = 0.1
        max_wait = 2
        tries = 0
        with self._get_conn() as conn:
            row_id = None
            obj_buffer = None
            while keep_pooling:
                conn.execute(self._write_lock)
                cursor = conn.execute(self._get)
                row = cursor.fetchone()
                if row:
                    row_id, obj_buffer = row
                    keep_pooling = False
                else:
                    conn.commit()  # unlock the database
                    if not sleep_wait:
                        keep_pooling = False
                        continue
                    tries += 1
                    sleep(wait)
                    wait = min(max_wait, tries / 10 + wait)
            if row_id:
                conn.execute(self._del, (row_id,))
                return loads(obj_buffer)
        return None

    def peek(self) -> Optional[Any]:
        with self._get_conn() as conn:
            row = conn.execute(self._peek).fetchone()
            if row:
                return loads(row[0])
            return None
