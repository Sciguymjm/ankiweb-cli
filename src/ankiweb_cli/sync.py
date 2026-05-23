from __future__ import annotations

import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import keyring
from anki.collection import Collection
from anki.sync_pb2 import SyncAuth, SyncCollectionResponse

SERVICE = "ankiweb-cli"


def store_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE, username, password)


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE, username)


@dataclass
class SyncResult:
    pulled: bool
    pushed: bool
    new_endpoint: str | None = None
    required_full_sync: bool = False
    server_message: str = ""


def login_and_get_hkey(
    username: str, password: str, endpoint: str
) -> tuple[str, str]:
    """Authenticate with AnkiWeb. Returns (hkey, endpoint)."""
    with tempfile.TemporaryDirectory(prefix="ankiweb-cli-login-") as tmp:
        tmp_col_path = Path(tmp) / "throwaway.anki2"
        col = Collection(str(tmp_col_path))
        try:
            auth = col.sync_login(
                username=username, password=password, endpoint=endpoint
            )
            return auth.hkey, (auth.endpoint or endpoint)
        finally:
            col.close()


def do_sync(
    col: Collection,
    hkey: str,
    endpoint: str,
    *,
    on_media_progress: Callable[[Any], None] | None = None,
    poll_interval: float = 1.0,
) -> SyncResult:
    auth = SyncAuth(hkey=hkey, endpoint=endpoint)
    out = col.sync_collection(auth, sync_media=True)
    required_full = out.required in (
        SyncCollectionResponse.FULL_SYNC,
        SyncCollectionResponse.FULL_DOWNLOAD,
        SyncCollectionResponse.FULL_UPLOAD,
    )
    # sync_collection kicks off media sync as a background task and returns
    # immediately. Block until that task finishes so the function only returns
    # once media is actually on the server.
    if not required_full:
        wait_for_media_sync(
            col, on_progress=on_media_progress, poll_interval=poll_interval
        )
    return SyncResult(
        pulled=True,
        pushed=True,
        new_endpoint=out.new_endpoint or None,
        required_full_sync=required_full,
        server_message=out.server_message or "",
    )


def wait_for_media_sync(
    col: Collection,
    *,
    on_progress: Callable[[Any], None] | None = None,
    poll_interval: float = 1.0,
) -> None:
    while True:
        status = col.media_sync_status()
        if on_progress is not None:
            on_progress(status)
        if not getattr(status, "active", False):
            return
        time.sleep(poll_interval)


def do_full_sync(
    col_path: Path,
    backups_dir: Path,
    *,
    username: str,
    password: str,
    endpoint: str,
    upload: bool,
) -> dict[str, object]:
    """Force a full upload or download. Replaces local collection on download.

    Logs in on the real Collection (no throwaway), runs sync_collection so the
    backend captures server state, then close_for_full_sync, then
    full_upload_or_download.
    """
    backups_dir.mkdir(parents=True, exist_ok=True)
    if col_path.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        direction = "upload" if upload else "download"
        shutil.copy2(col_path, backups_dir / f"collection-{ts}-full-{direction}.anki2")
    col_path.parent.mkdir(parents=True, exist_ok=True)
    col = Collection(str(col_path))
    try:
        auth = col.sync_login(username=username, password=password, endpoint=endpoint)
        out = col.sync_collection(auth, sync_media=False)
        server_usn = out.server_media_usn
        # sync_collection performs a 308-redirect from sync.ankiweb.net to a
        # numbered shard (e.g. sync15.ankiweb.net) and returns the resolved URL
        # in new_endpoint.  full_upload_or_download creates a fresh HTTP client
        # from auth.endpoint, so we must point auth at the shard before calling
        # it; otherwise the download request lands on the load-balancer which
        # returns a 303 with no body/headers, causing "missing original size".
        resolved_endpoint = out.new_endpoint or endpoint
        auth_for_full = SyncAuth(hkey=auth.hkey, endpoint=resolved_endpoint)
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth_for_full, server_usn=server_usn, upload=upload)
    finally:
        try:
            col.close()
        except Exception:
            pass
    return {
        "ok": True,
        "direction": "upload" if upload else "download",
        "endpoint": resolved_endpoint,
    }
