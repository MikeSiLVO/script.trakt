import os
import sqlite3
import logging
import threading
from json import loads, dumps
from _thread import get_ident

import xbmcvfs
import xbmcaddon

logger = logging.getLogger(__name__)

__addon__ = xbmcaddon.Addon("script.trakt")

MAX_RETRIES = 50


class ScrobbleQueue:
    """Persists failed stop-scrobbles for later retry via sync/history."""

    _create = (
        "CREATE TABLE IF NOT EXISTS failed_scrobbles ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  media_type TEXT NOT NULL,"
        "  media_info TEXT NOT NULL,"
        "  show_info TEXT,"
        "  watched_at TEXT NOT NULL,"
        "  progress REAL NOT NULL,"
        "  created_at REAL NOT NULL,"
        "  retry_count INTEGER DEFAULT 0"
        ")"
    )

    def __init__(self):
        self.path = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
        if not xbmcvfs.exists(self.path):
            xbmcvfs.mkdir(self.path)
        self.path = os.path.join(self.path, "queue.db")
        self._connection_cache = {}
        with self._get_conn() as conn:
            conn.execute(self._create)

    def _get_conn(self):
        tid = get_ident()
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

    def add(self, media_type, media_info, show_info, progress, watched_at):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO failed_scrobbles "
                "(media_type, media_info, show_info, watched_at, progress, created_at) "
                "VALUES (?, ?, ?, ?, ?, strftime('%s', 'now'))",
                (
                    media_type,
                    dumps(media_info),
                    dumps(show_info) if show_info else None,
                    watched_at,
                    progress,
                ),
            )
        logger.info("Queued failed %s scrobble for retry" % media_type)

    def get_pending(self):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, media_type, media_info, show_info, watched_at, progress, retry_count "
                "FROM failed_scrobbles ORDER BY id"
            ).fetchall()
        return [
            {
                "id": r[0],
                "media_type": r[1],
                "media_info": loads(r[2]),
                "show_info": loads(r[3]) if r[3] else None,
                "watched_at": r[4],
                "progress": r[5],
                "retry_count": r[6],
            }
            for r in rows
        ]

    def remove(self, row_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM failed_scrobbles WHERE id = ?", (row_id,))

    def increment_retry(self, row_id):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE failed_scrobbles SET retry_count = retry_count + 1 WHERE id = ?",
                (row_id,),
            )
            row = conn.execute(
                "SELECT retry_count FROM failed_scrobbles WHERE id = ?", (row_id,)
            ).fetchone()
            if row and row[0] > MAX_RETRIES:
                conn.execute(
                    "DELETE FROM failed_scrobbles WHERE id = ?", (row_id,)
                )
                logger.warning(
                    "Dropped scrobble after %d retries" % MAX_RETRIES
                )

    def __len__(self):
        with self._get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM failed_scrobbles"
            ).fetchone()[0]
