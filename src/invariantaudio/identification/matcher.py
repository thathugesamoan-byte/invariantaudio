# SPDX-License-Identifier: GPL-3.0-or-later
"""
Candidate matching and MusicBrainz query abstractions.
"""

def sanitize_search_query(text: str) -> str:
    """Strip promotional strings, bracketed download tags, and track numbers."""
    import re
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    cleaned = re.sub(r"^\d+[\s\-_.]+", "", cleaned)
    return cleaned.strip()
