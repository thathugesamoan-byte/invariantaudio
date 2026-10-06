# SPDX-License-Identifier: GPL-3.0-or-later
"""
Multi-Vector Candidate Scorer with strict margin and duration gates.
"""

def calculate_composite_score(
    acoustic_sim: float,
    title_sim: float,
    artist_sim: float,
    album_match: bool
) -> float:
    return (0.40 * acoustic_sim) + (0.30 * title_sim) + (0.20 * artist_sim) + (0.10 * (1.0 if album_match else 0.0))

def passes_duration_gate(file_dur: float, cand_dur: float, tolerance: float = 3.0) -> bool:
    return abs(file_dur - cand_dur) <= tolerance

def evaluate_auto_approval_eligibility(
    top_score: float,
    runner_up_score: float,
    overlap_frames: int,
    file_dur: float,
    cand_dur: float
) -> bool:
    if not passes_duration_gate(file_dur, cand_dur, 2.0):
        return False
    if overlap_frames < 150:
        return False
    if top_score < 0.80 or runner_up_score > 0.20:
        return False
    return (top_score - runner_up_score) >= 0.60
