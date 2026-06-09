"""Tests for scoring normalizer."""

from __future__ import annotations

import pytest

from startupintel.scoring.normalizer import normalize_signal


@pytest.mark.parametrize("input_val,min_val,max_val,expected", [
    (50, 0, 100, 50.0),
    (0, 0, 100, 0.0),
    (100, 0, 100, 100.0),
    (25, 0, 50, 50.0),
    (75, 50, 100, 50.0),
])
def test_normalize_score(input_val, min_val, max_val, expected):
    """Test score normalization."""
    result = normalize_signal(input_val, min_val, max_val, inverse=False)
    assert abs(result - expected) < 0.01


def test_normalize_signal_inverse():
    """Test inverse signal normalization."""
    # Higher input should give lower score when inverse=True
    result = normalize_signal(90, 0, 100, inverse=True)
    assert result < 50  # Should be low score for high input

    result = normalize_signal(10, 0, 100, inverse=True)
    assert result > 50  # Should be high score for low input


def test_normalize_signal_clamping():
    """Test that signals are clamped to 0-100 range."""
    # Below min should clamp to 0
    result = normalize_signal(-10, 0, 100)
    assert result == 0.0

    # Above max should clamp to 100
    result = normalize_signal(110, 0, 100)
    assert result == 100.0
