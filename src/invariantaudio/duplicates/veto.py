# SPDX-License-Identifier: GPL-3.0-or-later
"""
Live Veto & Version Gate.
"""

VETO_KEYWORDS = {"live", "remix", "tribute", "cover", "acoustic", "karaoke", "instrumental"}

def check_version_veto(source_title: str, candidate_title: str) -> bool:
    """Return True if a version discrepancy exists (e.g. Live matching Studio)."""
    src_lower = source_title.lower()
    cand_lower = candidate_title.lower()
    for kw in VETO_KEYWORDS:
        if (kw in src_lower and kw not in cand_lower) or (kw in cand_lower and kw not in src_lower):
            return True
    return False
