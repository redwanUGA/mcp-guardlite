import pytest
from mcpguardlite.eval.metrics import Episode, tsr, rsr, rcg, sfr


def ep(fired, success, asserted=None):
    return Episode("e", "c", fired, success,
                   asserted if asserted is not None else success,
                   0, 0, 0.0, None, [])


def test_rsr_excludes_untriggered():
    eps = [ep(False, True), ep(True, False), ep(True, True)]
    assert rsr(eps) == pytest.approx(0.5)
    assert tsr(eps) == pytest.approx(1.0)


def test_rcg_sign():
    """Recovery degrades more than nominal -> positive RCG."""
    base = [ep(False, True)] * 10 + [ep(True, True)] * 10
    comp = ([ep(False, True)] * 9 + [ep(False, False)]
            + [ep(True, True)] * 5 + [ep(True, False)] * 5)
    assert rcg(base, comp) > 0


def test_sfr_counts_only_false_assertions():
    assert sfr([ep(True, False, asserted=True), ep(True, True)]) == pytest.approx(0.5)
