"""
CFA Prep CLI - Tests for the BA II Plus calculator module
Author: CodeBuddy AI Assistant
Purpose: Check the financial calculator and its expression parser.
"""

import math
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.baii_calculator import (
    BAIIPlus,
    _eval_expr,  # pyright: ignore[reportPrivateUsage]
)


def test_baii_calculator():
    """Test the BA II Plus calculator emulator's TVM, NPV/IRR, and stats."""
    calc = BAIIPlus()

    # TVM: FV of 1000 at 5% for 10 years (compounded annually).
    # BA II Plus sign convention: an inflow today (+PV) implies an outflow later (-FV).
    calc.n, calc.iy, calc.pv, calc.pmt, calc.fv = 10, 5, 1000, 0, 0
    fv = calc.compute_tvm("FV")
    assert abs(fv + 1000 * 1.05**10) < 0.01, f"FV mismatch: {fv}"

    # Solve PV back: FV is now negative, so PV returns to +1000
    calc.fv = fv
    pv = calc.compute_tvm("PV")
    assert abs(pv - 1000) < 0.01, f"PV mismatch: {pv}"

    # PMT of an annuity: PV=1000, N=5, I/Y=10 -> PMT (negative cash outflow)
    calc.n, calc.iy, calc.pv, calc.fv = 5, 10, 1000, 0
    pmt = calc.compute_tvm("PMT")
    expected_pmt = 1000 * 0.10 / (1 - 1.10**-5)
    assert abs(pmt + expected_pmt) < 0.01, f"PMT mismatch: {pmt}"

    # Solve I/Y from the annuity values
    calc.n, calc.pv, calc.pmt, calc.fv = 5, 1000, -expected_pmt, 0
    iy = calc.compute_tvm("IY")
    assert abs(iy - 10) < 0.01, f"IY mismatch: {iy}"

    # NPV / IRR: invest 1000, receive 300 x4
    calc.clear_cashflows()
    for amt in (-1000, 300, 300, 300, 300):
        calc.add_cashflow(amt)
    npv = calc.npv(10)
    assert npv < 0, "NPV at 10% should be negative for this cash-flow series"
    irr = calc.irr()
    assert abs(irr - 7.71) < 0.1, f"IRR mismatch: {irr}"

    # One-variable stats
    calc.clear_data()
    for x in (1, 2, 3, 4, 5):
        calc.add_data(x)
    s = calc.one_var_stats()
    assert abs(s["mean"] - 3.0) < 1e-9
    # BA II Plus reports Sx as the sample standard deviation (n-1 denominator).
    assert abs(s["s_x"] - math.sqrt(2.5)) < 1e-9, f"Sx mismatch: {s['s_x']}"

    # Two-variable regression slope for y = 2x + 1
    calc.clear_data()
    for x in (1, 2, 3):
        calc.add_data(x, 2 * x + 1)
    s2 = calc.two_var_stats()
    assert abs(s2["slope"] - 2.0) < 1e-9
    assert abs(s2["intercept"] - 1.0) < 1e-9
    assert abs(s2["correlation"] - 1.0) < 1e-9

    # Percent change
    assert abs(calc.percent_change(50, 75) - 50.0) < 1e-9

    # Raw arithmetic expressions
    assert abs(_eval_expr("1+2") - 3) < 1e-9
    assert abs(_eval_expr("10*5") - 50) < 1e-9
    assert abs(_eval_expr("2^10") - 1024) < 1e-9
    assert abs(_eval_expr("3*(4-1)^2") - 27) < 1e-9
    assert abs(_eval_expr("100/3") - 100 / 3) < 1e-9
    assert abs(_eval_expr("-5+2") - (-3)) < 1e-9
    print("  ✅ BA II Plus calculator is fine")
