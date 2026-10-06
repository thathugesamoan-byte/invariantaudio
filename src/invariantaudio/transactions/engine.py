# SPDX-License-Identifier: GPL-3.0-or-later
"""
Journaled mutation engine for metadata-only tag writes plus relocation.

Guarantees and limits are documented in docs/transaction-model.md. In short:

* The target path is never overwritten: installation is a hard link
  (``os.link``), which fails if the destination exists.
* Every step is journaled in ``production_transactions`` before it happens.
* The source file is retired only after the SQLite commit that records the
  track, so a database failure never costs the original.
* Staging and target must be on the same filesystem (enforced).
"""

import errno
import os
import sqlite3
import stat
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TDRC, TIT2, TPE1, TRCK
from mutagen.mp4 import MP4

from invariantaudio.fsutil import copy_exclusive as _copy_exclusive, fsync_dir as _fsync_dir, fsync_file as _fsync_file
from invariantaudio.integrity.audio_integrity import (
    compute_compressed_audio_payload_sha256,
    compute_decoded_pcm_sha256,
    compute_file_sha256,
    inspect_stream_health,
)
from invariantaudio.recovery.recovery_manager import (
    recover_transaction,
    require_schema,
    unresolved_transactions,
)
from invariantaudio.transactions.lock import MutationLock
from invariantaudio.transactions.source_continuity import (
    SourceBindingTuple,
    capture_source_binding,
    verify_source_continuity,
)

SUPPORTED_EXTENSIONS = frozenset({".mp3", ".m4a"})
SUPPORTED_TAGS = frozenset({"title", "artist", "album", "year", "track_number"})
DEFAULT_BATCH_SIZE_LIMIT = 10

# Target classification (see classify_target)
TARGET_ABSENT = "ABSENT"
TARGET_IS_SOURCE = "IS_SOURCE"
TARGET_ALIASES_SOURCE = "ALIASES_SOURCE"
TARGET_IDENTICAL = "EXISTS_IDENTICAL"
TARGET_DIFFERENT = "EXISTS_DIFFERENT"
TARGET_NOT_REGULAR = "EXISTS_NOT_REGULAR"
TARGET_NAME_COLLISION = "NAME_COLLISION"


class TransactionError(RuntimeError):
    """Raised when a proposal is refused or fails. ``code`` is machine-readable;
    ``completed`` lists results of proposals already committed in the same batch."""

    def __init__(self, code: str, message: str, completed: Optional[List[Dict[str, Any]]] = None):
        super().__init__(f"MUTATION_FAILED {code}: {message}")
        self.code = code
        self.detail = message
        self.completed = completed or []


def normalize_path_unicode(p: str | Path) -> Path:
    return Path(unicodedata.normalize("NFC", str(p)))


def _fold(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def _nearest_existing(path: str) -> str:
    p = path
    while not os.path.lexists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return p


def _name_collision(tgt: str) -> Optional[str]:
    """Return a colliding sibling for any path component of ``tgt`` that does not
    exist byte-exactly but is equivalent under Unicode NFC + case folding."""
    parts = Path(tgt).parts
    cur = parts[0]
    for comp in parts[1:]:
        nxt = os.path.join(cur, comp)
        if os.path.lexists(nxt):
            cur = nxt
            continue
        try:
            siblings = os.listdir(cur)
        except OSError:
            return None
        for s in siblings:
            if _fold(s) == _fold(comp):
                return os.path.join(cur, s)
        return None  # nothing deeper can exist
    return None


def classify_target(src: str | Path, tgt: str | Path) -> str:
    """Classify the destination of a proposed move without modifying anything."""
    src_s, tgt_s = os.path.abspath(str(src)), os.path.abspath(str(tgt))
    if src_s == tgt_s:
        return TARGET_IS_SOURCE
    if os.path.lexists(tgt_s):
        try:
            tst = os.lstat(tgt_s)
        except OSError:
            return TARGET_NOT_REGULAR
        if not stat.S_ISREG(tst.st_mode):
            return TARGET_NOT_REGULAR
        try:
            sst = os.lstat(src_s)
            if (sst.st_dev, sst.st_ino) == (tst.st_dev, tst.st_ino):
                return TARGET_ALIASES_SOURCE
        except OSError:
            pass
        try:
            if compute_file_sha256(src_s) == compute_file_sha256(tgt_s):
                return TARGET_IDENTICAL
        except OSError:
            return TARGET_NOT_REGULAR
        return TARGET_DIFFERENT
    collision = _name_collision(tgt_s)
    if collision is not None:
        # A sibling that is the source itself under an equivalent name is an alias.
        try:
            if os.path.samefile(collision, src_s) and not os.path.isdir(collision):
                return TARGET_ALIASES_SOURCE
        except OSError:
            pass
        return TARGET_NAME_COLLISION
    return TARGET_ABSENT


def _device(path: str) -> int:
    return os.stat(path).st_dev


class TransactionEngine:
    def __init__(
        self,
        db_conn: sqlite3.Connection,
        backup_root: Path,
        staging_root: Path,
        lock_path: Path,
        media_root: Optional[Path] = None,
        batch_size_limit: int = DEFAULT_BATCH_SIZE_LIMIT,
    ):
        if isinstance(batch_size_limit, bool) or not isinstance(batch_size_limit, int) or batch_size_limit < 1:
            raise ValueError("batch_size_limit must be a positive integer")
        self.conn = db_conn
        self.backup_root = Path(backup_root)
        self.staging_root = Path(staging_root)
        self.lock_path = Path(lock_path)
        self.media_root = Path(media_root) if media_root is not None else None
        self.batch_size_limit = batch_size_limit

    # ------------------------------------------------------------------ batch
    def apply_batch(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply proposals sequentially under the exclusive lock.

        All proposals are validated structurally before anything is touched.
        Processing stops at the first failure; earlier commits remain and are
        reported in ``TransactionError.completed``.
        """
        if len(proposals) > self.batch_size_limit:
            raise TransactionError("BATCH_TOO_LARGE", f"{len(proposals)} > limit {self.batch_size_limit}")
        planned = [self._validate_structure(p) for p in proposals]
        seen_t: Dict[str, str] = {}
        seen_s = set()
        for s, t, _ in planned:
            key = _fold(str(t))
            if key in seen_t:
                raise TransactionError("DUPLICATE_TARGET_IN_BATCH", str(t))
            if str(s) in seen_s:
                raise TransactionError("DUPLICATE_SOURCE_IN_BATCH", str(s))
            seen_t[key] = str(s)
            seen_s.add(str(s))

        results: List[Dict[str, Any]] = []
        with MutationLock(self.lock_path):
            require_schema(self.conn)
            if self.conn.in_transaction:
                raise TransactionError("CALLER_TRANSACTION_OPEN", "commit or roll back before applying a batch")
            pending = unresolved_transactions(self.conn)
            if pending:
                ids = ", ".join(str(p["transaction_id"]) for p in pending)
                raise TransactionError("UNRESOLVED_TRANSACTIONS", f"run recovery first (ids: {ids})")
            for src, tgt, tags in planned:
                try:
                    results.append(self._apply_single(src, tgt, tags))
                except TransactionError as e:
                    e.completed = list(results)
                    raise
        return results

    def recover(self) -> List[Dict[str, Any]]:
        """Resolve interrupted transactions under the exclusive lock."""
        from invariantaudio.recovery.recovery_manager import recover_interrupted_transactions

        with MutationLock(self.lock_path):
            return recover_interrupted_transactions(self.conn, self.staging_root)

    # ------------------------------------------------------------- validation
    def _validate_structure(self, prop: Dict[str, Any]) -> Tuple[Path, Path, Dict[str, str]]:
        try:
            src = Path(prop["source_path"])
            tgt = normalize_path_unicode(prop["target_path"])
        except (KeyError, TypeError):
            raise TransactionError("INVALID_PROPOSAL", "source_path and target_path are required")
        tags = prop.get("tags", {}) or {}
        if not isinstance(tags, dict):
            raise TransactionError("INVALID_PROPOSAL", "tags must be a mapping")
        for k, v in tags.items():
            if k not in SUPPORTED_TAGS:
                raise TransactionError("UNSUPPORTED_TAG", str(k))
            if isinstance(v, bool) or not isinstance(v, (str, int)):
                raise TransactionError("INVALID_TAG_VALUE", f"{k}: {type(v).__name__}")
        s_ext, t_ext = src.suffix.lower(), tgt.suffix.lower()
        if s_ext not in SUPPORTED_EXTENSIONS:
            raise TransactionError("UNSUPPORTED_MEDIA_EXTENSION", f"source {s_ext or '(none)'}")
        if t_ext != s_ext:
            raise TransactionError("UNSUPPORTED_MEDIA_EXTENSION", f"target {t_ext or '(none)'} must equal source {s_ext}")
        return src, tgt, {k: str(v) for k, v in tags.items()}

    def _check_containment(self, tgt: str) -> None:
        if self.media_root is None:
            return
        root = os.path.realpath(self.media_root)
        anchor = os.path.realpath(_nearest_existing(os.path.dirname(tgt)))
        if not (anchor == root or anchor.startswith(root + os.sep)):
            raise TransactionError("TARGET_OUTSIDE_MEDIA_ROOT", tgt)

    # --------------------------------------------------------------- journal
    def _journal(self, tid: int, state: str, **fields: Any) -> None:
        sets = ["state = ?", "updated_utc = CURRENT_TIMESTAMP"]
        vals: List[Any] = [state]
        for k, v in fields.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(tid)
        self.conn.execute(f"UPDATE production_transactions SET {', '.join(sets)} WHERE transaction_id = ?", vals)
        self.conn.commit()

    # ------------------------------------------------------------- one proposal
    def _apply_single(self, src: Path, tgt: Path, tags: Dict[str, str]) -> Dict[str, Any]:
        src_s = os.path.abspath(str(src))
        tgt_s = os.path.abspath(str(tgt))

        # Pre-journal checks: nothing is created or modified if any of them fails.
        self._check_containment(tgt_s)
        try:
            binding = capture_source_binding(src_s)
        except (OSError, ValueError) as e:
            raise TransactionError("SOURCE_REJECTED", str(e))
        verdict = classify_target(src_s, tgt_s)
        if verdict != TARGET_ABSENT:
            raise TransactionError(f"TARGET_{verdict}", tgt_s)
        if self.conn.execute("SELECT 1 FROM tracks WHERE canonical_path = ?", (tgt_s,)).fetchone():
            raise TransactionError("TARGET_ALREADY_INDEXED", tgt_s)
        self.staging_root.mkdir(parents=True, exist_ok=True)
        anchor = _nearest_existing(os.path.dirname(tgt_s))
        if _device(str(self.staging_root)) != _device(anchor):
            raise TransactionError("CROSS_FILESYSTEM_STAGING", f"staging_root and {anchor} are on different devices")
        status, diag = inspect_stream_health(src_s)
        if status == "UNUSABLE":
            raise TransactionError("UNUSABLE_SOURCE", diag[:200])
        try:
            pre_payload = compute_compressed_audio_payload_sha256(src_s)
            pre_pcm = compute_decoded_pcm_sha256(src_s)
        except RuntimeError as e:
            raise TransactionError("SOURCE_HASHING_FAILED", str(e)[:200])

        # Journal first.
        cur = self.conn.execute(
            "INSERT INTO production_transactions (state, source_path, target_path, source_sha256, "
            "source_payload_sha256, source_pcm_sha256, verification_status) VALUES ('PLANNED', ?, ?, ?, ?, ?, ?)",
            (src_s, tgt_s, binding.whole_file_sha256, pre_payload, pre_pcm, status),
        )
        tid = cur.lastrowid
        assert tid is not None
        self.conn.commit()
        sha12 = binding.whole_file_sha256[:12]
        backup_path = str(self.backup_root / f"{tid}_{sha12}_{src.name}")
        staging_path = str(self.staging_root / f"staging_{tid}_{sha12}{src.suffix.lower()}")
        self._journal(tid, "PLANNED", backup_path=backup_path, staging_path=staging_path)

        try:
            self._backup_and_stage(src_s, binding, backup_path, staging_path)
            self._journal(tid, "STAGED")

            self._write_metadata(Path(staging_path), tags)
            post_payload = compute_compressed_audio_payload_sha256(staging_path)
            if post_payload != pre_payload:
                raise TransactionError("PAYLOAD_MISMATCH", f"{post_payload} != {pre_payload}")
            post_pcm = compute_decoded_pcm_sha256(staging_path)
            if post_pcm != pre_pcm:
                raise TransactionError("PCM_MISMATCH", f"{post_pcm} != {pre_pcm}")
            _fsync_file(staging_path)
            staged_sha = compute_file_sha256(staging_path)
            self._journal(tid, "VERIFIED", staged_sha256=staged_sha)

            # Source continuity is re-validated immediately before the first
            # change to the media tree.
            if not verify_source_continuity(binding):
                raise TransactionError("SOURCE_CHANGED", "source no longer matches its binding")
            self._install(staging_path, tgt_s, staged_sha)
            self._journal(tid, "INSTALLED")

            self._commit_track(tid, tgt_s, src_s, staged_sha, post_payload, status)
        except BaseException as e:
            if not isinstance(e, Exception):
                raise  # simulated/real hard stop: leave the journal for recovery
            self._fail(tid, e)
            raise  # unreachable; _fail always raises

        retired = self._retire_source(tid, src_s, binding)
        return {
            "status": "COMMITTED" if retired else "COMMITTED_SOURCE_RETAINED",
            "transaction_id": tid,
            "source_path": src_s,
            "target_path": tgt_s,
            "file_sha256": staged_sha,
            "payload_sha256": post_payload,
            "pcm_sha256": post_pcm,
            "verification_status": status,
            "backup_path": backup_path,
            "source_retired": retired,
        }

    def _fail(self, tid: int, err: Exception) -> None:
        try:
            self.conn.rollback()
        except sqlite3.Error:
            pass
        code = err.code if isinstance(err, TransactionError) else type(err).__name__
        try:
            state = self.conn.execute(
                "SELECT state FROM production_transactions WHERE transaction_id = ?", (tid,)
            ).fetchone()[0]
            if state == "COMMITTED":
                # The failed step was not the commit itself; nothing to roll back.
                raise TransactionError("POST_COMMIT_FAILURE", str(err))
            self.conn.execute(
                "UPDATE production_transactions SET detail = ? WHERE transaction_id = ?",
                (f"error: {code}: {err}"[:500], tid),
            )
            self.conn.commit()
            final = recover_transaction(self.conn, tid, self.staging_root)
        except TransactionError:
            raise
        except Exception as rec_err:
            raise TransactionError(
                "ROLLBACK_INCOMPLETE",
                f"transaction {tid} left in-flight; run recovery. cause={code}; recovery error={rec_err}",
            )
        if final == "NEEDS_REVIEW":
            raise TransactionError("ROLLBACK_NEEDS_REVIEW", f"transaction {tid}; cause={code}")
        detail = err.detail if isinstance(err, TransactionError) else str(err)
        raise TransactionError(code, f"{detail} (transaction {tid} {final})")

    # ------------------------------------------------------------ file steps
    def _backup_and_stage(self, src: str, binding: SourceBindingTuple, backup: str, staging: str) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        _copy_exclusive(src, backup)
        _copy_exclusive(src, staging)
        # Both copies must equal the bound source content.
        for p in (backup, staging):
            if compute_file_sha256(p) != binding.whole_file_sha256:
                raise TransactionError("SOURCE_CHANGED", f"copy {os.path.basename(p)} does not match bound source")
        _fsync_dir(str(self.backup_root))

    def _install(self, staging: str, tgt: str, staged_sha: str) -> None:
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        try:
            os.link(staging, tgt)  # atomic; raises FileExistsError instead of replacing
        except FileExistsError:
            raise TransactionError("TARGET_EXISTS_AT_INSTALL", tgt)
        except OSError as e:
            if e.errno == errno.EXDEV:
                raise TransactionError("CROSS_FILESYSTEM_STAGING", tgt)
            raise TransactionError("INSTALL_FAILED", f"{tgt}: {e}")
        _fsync_dir(os.path.dirname(tgt))
        if compute_file_sha256(tgt) != staged_sha:
            raise TransactionError("INSTALLED_HASH_MISMATCH", tgt)
        os.unlink(staging)

    def _commit_track(self, tid: int, tgt: str, src: str, file_sha: str, payload_sha: str, status: str) -> None:
        """Insert the track and mark the journal COMMITTED in one SQLite transaction."""
        try:
            if not self.conn.in_transaction:
                self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute(
                "INSERT INTO tracks (canonical_path, original_path, sha256, compressed_audio_sha256, "
                "verification_status) VALUES (?, ?, ?, ?, ?)",
                (tgt, src, file_sha, payload_sha, status),
            )
            self.conn.execute(
                "UPDATE production_transactions SET state = 'COMMITTED', updated_utc = CURRENT_TIMESTAMP "
                "WHERE transaction_id = ?",
                (tid,),
            )
            self.conn.commit()
        except Exception as e:
            # A failed COMMIT is not assumed to have rolled back; read the journal.
            try:
                self.conn.rollback()
            except sqlite3.Error:
                pass
            try:
                state = self.conn.execute(
                    "SELECT state FROM production_transactions WHERE transaction_id = ?", (tid,)
                ).fetchone()[0]
            except Exception:
                raise TransactionError("COMMIT_OUTCOME_UNKNOWN", f"transaction {tid}: {e}")
            if state != "COMMITTED":
                raise TransactionError("DATABASE_COMMIT_FAILED", str(e))

    def _retire_source(self, tid: int, src: str, binding: SourceBindingTuple) -> bool:
        """Remove the original only after the commit, and only if it is unchanged.
        Failure leaves the transaction COMMITTED; recovery finishes it."""
        try:
            if not verify_source_continuity(binding):
                return False
            os.unlink(src)
            _fsync_dir(os.path.dirname(src))
            self._journal(tid, "COMPLETED")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ tags
    def _write_metadata(self, path: Path, tags: Dict[str, Any]) -> None:
        ext = path.suffix.lower()
        if ext == ".mp3":
            try:
                audio = ID3(path)
            except ID3NoHeaderError:
                audio = ID3()
            if "title" in tags:
                audio["TIT2"] = TIT2(encoding=3, text=[tags["title"]])
            if "artist" in tags:
                audio["TPE1"] = TPE1(encoding=3, text=[tags["artist"]])
            if "album" in tags:
                audio["TALB"] = TALB(encoding=3, text=[tags["album"]])
            if "year" in tags:
                audio["TDRC"] = TDRC(encoding=3, text=[str(tags["year"])])
            if "track_number" in tags:
                audio["TRCK"] = TRCK(encoding=3, text=[str(tags["track_number"])])
            audio.save(path, v2_version=4)
        elif ext == ".m4a":
            mp4 = MP4(path)
            if "title" in tags:
                mp4["\xa9nam"] = [tags["title"]]
            if "artist" in tags:
                mp4["\xa9ART"] = [tags["artist"]]
            if "album" in tags:
                mp4["\xa9alb"] = [tags["album"]]
            if "year" in tags:
                mp4["\xa9day"] = [str(tags["year"])]
            if "track_number" in tags:
                num, _, total = str(tags["track_number"]).partition("/")
                try:
                    mp4["trkn"] = [(int(num), int(total) if total else 0)]
                except ValueError:
                    raise TransactionError("INVALID_TAG_VALUE", f"track_number: {tags['track_number']!r}")
            mp4.save()
        else:
            raise TransactionError("UNSUPPORTED_MEDIA_EXTENSION", ext)
