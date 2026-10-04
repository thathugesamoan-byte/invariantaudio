# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from invariantaudio.evidence.scorer import (
    calculate_composite_score,
    passes_duration_gate,
    evaluate_auto_approval_eligibility
)

def test_composite_scoring():
    score = calculate_composite_score(1.0, 1.0, 1.0, True)
    assert score == pytest.approx(1.0)

    score_half = calculate_composite_score(0.5, 0.5, 0.5, False)
    assert score_half == pytest.approx(0.45)

def test_duration_gate():
    assert passes_duration_gate(180.0, 181.5, tolerance=3.0) is True
    assert passes_duration_gate(180.0, 185.0, tolerance=3.0) is False

def test_auto_approval_margin_gate():
    assert evaluate_auto_approval_eligibility(0.90, 0.15, 200, 180.0, 180.5) is True
    assert evaluate_auto_approval_eligibility(0.85, 0.40, 200, 180.0, 180.5) is False
