from pre_filter import PreFilter


def test_regime_adjustment_initializes():
    pf = PreFilter(simulation_mode=True, fast_mode=True, regime_adjustment=True)
    assert pf.regime_adjustment is True
    assert pf.regime_filter is not None


if __name__ == "__main__":
    test_regime_adjustment_initializes()
    print("✅ Phase 2 regime integration test passed")
