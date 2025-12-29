"""
Tests for signal computation and evaluation.
"""

import pytest
from pam_world import WorldPAM, Config, SourceDef, SignalDef, HypothesisDef
from validators import validate_config


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return Config(
        sources=[
            SourceDef(name="test_source", url="https://example.com/feed", type="rss", timeout=10.0)
        ],
        signals=[
            SignalDef(name="test_signal", weight=1.0, description="Test", aggregation="sum", cap=1.0)
        ],
        hypotheses=[
            HypothesisDef(name="test_hypothesis", prior=0.1, signals=["test_signal"])
        ],
        keyword_sets={
            "test_keywords": ["test", "example"]
        },
        signal_bindings={
            "test_signal": {
                "sources": ["test_source"],
                "keywords": ["test_keywords"],
                "window_days": 7
            }
        }
    )


def test_config_validation_valid(sample_config):
    """Test validation of valid config."""
    errors = validate_config(sample_config)
    assert len(errors) == 0


def test_config_validation_invalid_signal_reference():
    """Test validation catches invalid signal reference."""
    config = Config(
        sources=[SourceDef(name="s1", url="https://example.com", type="rss")],
        signals=[SignalDef(name="s1", weight=1.0)],
        hypotheses=[HypothesisDef(name="h1", prior=0.1, signals=["nonexistent"])],
        keyword_sets={},
        signal_bindings={}
    )
    
    errors = validate_config(config)
    assert any("nonexistent" in e for e in errors)


def test_config_validation_invalid_source_reference():
    """Test validation catches invalid source reference."""
    config = Config(
        sources=[SourceDef(name="s1", url="https://example.com", type="rss")],
        signals=[SignalDef(name="sig1", weight=1.0)],
        hypotheses=[HypothesisDef(name="h1", prior=0.1, signals=["sig1"])],
        keyword_sets={"kw1": ["test"]},
        signal_bindings={
            "sig1": {
                "sources": ["nonexistent_source"],
                "keywords": ["kw1"],
                "window_days": 7
            }
        }
    )
    
    errors = validate_config(config)
    assert any("nonexistent_source" in e for e in errors)


def test_world_pam_initialization(sample_config):
    """Test WorldPAM initialization."""
    pam = WorldPAM(sample_config)
    assert pam.cfg == sample_config
    assert "test_source" in pam.sources
    assert "test_signal" in pam.signals
    assert "test_hypothesis" in pam.hyps


def test_compute_signal_missing_binding(sample_config):
    """Test signal computation with missing binding."""
    pam = WorldPAM(sample_config)
    # Should return 0.0 for missing signal
    result = pam.compute_signal("nonexistent_signal")
    assert result == 0.0


def test_evaluate_hypothesis(sample_config):
    """Test hypothesis evaluation."""
    pam = WorldPAM(sample_config)
    
    # Mock fetch to avoid network calls
    original_fetch = pam.compute_signal
    def mock_compute_signal(sig_name, country=None):
        return 0.5  # Mock signal value
    
    pam.compute_signal = mock_compute_signal
    
    p, mean, ci, details = pam.evaluate("test_hypothesis")
    
    assert 0.0 <= p <= 1.0
    assert len(details) > 0

