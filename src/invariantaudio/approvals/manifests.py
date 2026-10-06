# SPDX-License-Identifier: GPL-3.0-or-later
"""
Manifest hashing (canonical-JSON SHA-256, an integrity digest, not a signature)
and synthetic-identifier rejection. No approval workflow is built on these yet.
"""

import hashlib
import json
from typing import Dict, Any

def compute_manifest_hash(data: Dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def validate_synthetic_id_rejection(mbid: str) -> bool:
    """Strictly reject synthetic placeholder UUID patterns (e.g. b1b1c1d1-*)."""
    if not mbid:
        return True
    if mbid.startswith("b1b1c1d1") or "0000000000" in mbid:
        raise ValueError(f"SYNTHETIC_UUID_REJECTED: {mbid}")
    return True
