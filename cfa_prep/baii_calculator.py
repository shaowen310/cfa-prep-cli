# -*- coding: utf-8 -*-
"""
CFA Prep CLI - BA II Plus Financial Calculator emulator
Author: CodeBuddy AI Assistant
Purpose: Mimic the functionality of the Texas Instruments BA II Plus financial
         calculator used in the CFA exams, via an interactive button-style REPL.
"""

from __future__ import annotations

import math
from typing import Callable

NPV_TOL = 1e-6


def _solve_rate(
    objective: Callable[[float], float],
    lo: float,
    hi: float,
    max_iter: int = 200,
    tol: float = 1e-9,
) -> float | None:
    """Bisection search for a root of `objective` within [lo, hi]."""
    flo = objective(lo)
    fhi = objective(hi)
    if flo * fhi > 0:
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        fmid = objective(mid)
        if abs(fmid) < tol or abs(hi - lo) < tol:
            return mid
        if flo * fmid < 0:
            hi = mid
        else:
            lo = mid
            flo = fmid
    return (lo + hi) / 2.0


def _fmt(x: float) -> str:
    """Format a number like a calculator display (up to 4 decimals, trimmed)."""
    return f"{x:,.4f}".rstrip("0").rstrip(".")


class BAIIPlus:
    """Mimic a BA II Plus financial calculator's TVM and cash-flow keys."""

    def __init__(self) -> None:
        self.n: float = 0.0
        self.iy: float = 0.0
        self.pv: float = 0.0
        self.pmt: float = 0.0
        self.fv: float = 0.0
        self.cf: list[tuple[float, float]] = []   # [(amount, frequency)]
        self.data: list[tuple[float, float]] = []  # (x, y)
        self.pay_per_year: float = 1.0            # CFA default: 1

    # --- TVM --------------------------------------------------------------

    def compute_tvm(self, target: str) -> float:
        """Solve the TVM equation for the register `target` (N/IY/PV/PMT/FV).
        Equation: PV + PMT*[(1-(1+i)^-N)/i] + FV*(1+i)^-N = 0, i = IY/(100*P/Y)."""
        t = target.upper()
        i_rate = self.iy / 100.0 / self.pay_per_year
        n = self.n * self.pay_per_year

        if t in ("IY", "I/Y"):
            return self._solve_iy()

        if t == "N":
            if abs(i_rate) < 1e-12:
                if abs(self.pmt) < 1e-12:
                    raise ValueError("Cannot solve N when PMT=0 and IY=0")
                return -(self.pv + self.fv) / self.pmt / self.pay_per_year
            base = (self.pmt * (1 + i_rate) - self.fv * i_rate) / (
                self.pmt + self.pv * i_rate
            )
            if base <= 0:
                raise ValueError("No valid N (log argument non-positive)")
            return math.log(base) / math.log(1 + i_rate) / self.pay_per_year

        if abs(i_rate) < 1e-12:
            if t == "PV":
                return -(self.pmt * n + self.fv)
            if t == "FV":
                return -(self.pv + self.pmt * n)
            if t == "PMT":
                if abs(n) < 1e-12:
                    raise ValueError("Cannot solve PMT when N=0")
                return -(self.pv + self.fv) / n
            raise ValueError(f"Unknown TVM register: {t}")

        discount = (1 + i_rate) ** -n
        annuity = (1 - discount) / i_rate
        if t == "PV":
            return -(self.pmt * annuity + self.fv * discount)
        if t == "FV":
            return -(self.pv + self.pmt * annuity) / discount
        if t == "PMT":
            if abs(annuity) < 1e-12:
                raise ValueError("Annuity factor is zero")
            return -(self.pv + self.fv * discount) / annuity
        raise ValueError(f"Unknown TVM register: {t}")

    def _solve_iy(self) -> float:
        """Solve IY (annual %) via bisection."""
        n = self.n * self.pay_per_year

        def f(rp: float) -> float:
            if abs(rp) < 1e-12:
                return self.pv + self.pmt * n + self.fv
            discount = (1 + rp) ** -n
            annuity = (1 - discount) / rp
            return self.pv + self.pmt * annuity + self.fv * discount

        root = _solve_rate(f, -0.999999, 1000.0)
        if root is None:
            raise ValueError("No interest rate found (no sign change)")
        return root * 100.0 * self.pay_per_year

    # --- Cash flows -------------------------------------------------------

    def add_cashflow(self, amount: float, frequency: float = 1.0) -> None:
        if frequency <= 0:
            raise ValueError("Frequency must be > 0")
        if not self.cf:
            self.cf.append((amount, 1.0))
        else:
            self.cf.append((amount, float(frequency)))

    def clear_cashflows(self) -> None:
        self.cf = []

    def npv(self, rate_pct: float) -> float:
        r = rate_pct / 100.0
        value, period = 0.0, 0.0
        for amount, freq in self.cf:
            for _ in range(int(freq)):
                value += amount / (1 + r) ** period
                period += 1.0
        return value

    def irr(self) -> float:
        if not self.cf:
            raise ValueError("No cash flows entered")
        signs = [1 if a > 0 else (-1 if a < 0 else 0) for a, _ in self.cf]
        if all(s >= 0 for s in signs) or all(s <= 0 for s in signs):
            raise ValueError("IRR requires both positive and negative cash flows")

        def f(r: float) -> float:
            value, period = 0.0, 0.0
            for amount, freq in self.cf:
                for _ in range(int(freq)):
                    value += amount / (1 + r) ** period
                    period += 1.0
            return value

        root = _solve_rate(f, -0.999999, 1000.0)
        if root is None:
            raise ValueError("IRR could not be found")
        return root * 100.0

    # --- Statistics -------------------------------------------------------

    def add_data(self, x: float, y: float | None = None) -> None:
        self.data.append((x, y if y is not None else 0.0))

    def clear_data(self) -> None:
        self.data = []

    def _moments(self, col: int) -> tuple[float, float]:
        vals = [d[col] for d in self.data]
        n = len(vals)
        if n == 0:
            raise ValueError("No data entered")
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n  # population variance
        return mean, math.sqrt(var)

    def one_var_stats(self) -> dict[str, float]:
        mean, sd = self._moments(0)
        return {"n": float(len(self.data)), "mean": mean, "pop_sd": sd}

    def two_var_stats(self) -> dict[str, float]:
        if len(self.data) < 2:
            raise ValueError("Need at least 2 data points for 2-V stats")
        n = float(len(self.data))
        xs = [d[0] for d in self.data]
        ys = [d[1] for d in self.data]
        mx, my = sum(xs) / n, sum(ys) / n
        sxy = sum((x - mx) * (y - my) for x, y in self.data)
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        slope = sxy / sxx if abs(sxx) > 1e-12 else 0.0
        intercept = my - slope * mx
        corr = sxy / math.sqrt(sxx * syy) if abs(sxx * syy) > 1e-12 else 0.0
        sx = math.sqrt(sxx / (n - 1))
        sy = math.sqrt(syy / (n - 1))
        return {
            "n": n, "mean_x": mx, "mean_y": my,
            "s_x": sx, "s_y": sy,
            "slope": slope, "intercept": intercept, "correlation": corr,
        }

    # --- Utility ----------------------------------------------------------

    def percent_change(self, old: float, new: float) -> float:
        if abs(old) < 1e-12:
            raise ValueError("Old value cannot be zero")
        return (new - old) / abs(old) * 100.0

    def reset(self) -> None:
        self.__init__()


def _print_help() -> None:
    print("""
  Commands (CFA-style BA II Plus):
    N <v>  IY <v>  PV <v>  PMT <v>  FV <v>   set a TVM register
    CPT <N|IY|PV|PMT|FV>                     solve a TVM register
    CF <amount> [freq]                       add a cash flow (CF0 = first)
    NPV <rate%>                              net present value
    IRR                                      internal rate of return
    STAT <x x x ...>                         one-variable statistics
    STAT2 <x y x y ...>                      two-variable statistics
    CHG <old> <new>                          percent change
    RESET                                    clear all registers
    HELP                                     this help
    QUIT / EXIT                              leave the calculator
""")


def run_repl() -> None:
    """Interactive prompt mimicking the BA II Plus keypad."""
    calc = BAIIPlus()
    print("\n" + "=" * 60)
    print("  🧮 BA II Plus Financial Calculator (CFA style)")
    print("=" * 60)
    print("  Type HELP for commands, QUIT to exit.\n")

    while True:
        try:
            line = input("  baii> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  👋 Exiting BA II Plus calculator.")
            return
        if not line:
            continue

        parts = line.split()
        cmd = parts[0].upper()
        try:
            if cmd in ("HELP", "?"):
                _print_help()
            elif cmd in ("QUIT", "EXIT", "Q"):
                print("  👋 Exiting BA II Plus calculator.")
                return
            elif cmd == "RESET":
                calc.reset()
                print("  ✅ Calculator reset.")
            elif cmd in ("N", "IY", "PV", "PMT", "FV"):
                value = float(parts[1])
                setattr(calc, "iy" if cmd == "IY" else cmd.lower(), value)
                print(f"  {cmd} = {_fmt(value)}")
            elif cmd == "CPT":
                target = parts[1].upper()
                print(f"  {target} = {_fmt(calc.compute_tvm(target))}")
            elif cmd == "CF":
                amount = float(parts[1])
                freq = float(parts[2]) if len(parts) > 2 else 1.0
                calc.add_cashflow(amount, freq)
                print(f"  CF[{len(calc.cf) - 1}] = {_fmt(amount)} (freq {freq:g})")
            elif cmd == "NPV":
                print(f"  NPV = {_fmt(calc.npv(float(parts[1])))}")
            elif cmd == "IRR":
                print(f"  IRR = {_fmt(calc.irr())}%")
            elif cmd == "STAT":
                xs = [float(p) for p in parts[1:]]
                calc.clear_data()
                for x in xs:
                    calc.add_data(x)
                s = calc.one_var_stats()
                print(f"  n={s['n']:g}  mean={_fmt(s['mean'])}  pop sd={_fmt(s['pop_sd'])}")
            elif cmd == "STAT2":
                nums = [float(p) for p in parts[1:]]
                if len(nums) % 2 != 0:
                    print("  ❌ STAT2 requires pairs of values (x y x y ...).")
                    continue
                calc.clear_data()
                for i in range(0, len(nums), 2):
                    calc.add_data(nums[i], nums[i + 1])
                s = calc.two_var_stats()
                print(f"  slope={_fmt(s['slope'])}  intercept={_fmt(s['intercept'])}"
                      f"  corr={_fmt(s['correlation'])}")
            elif cmd == "CHG":
                print(f"  CHG = {_fmt(calc.percent_change(float(parts[1]), float(parts[2])))}%")
            else:
                print(f"  ❌ Unknown command: {cmd}  (type HELP)")
        except (ValueError, ZeroDivisionError) as e:
            print(f"  ❌ {e}")
        except IndexError:
            print(f"  ❌ Not enough arguments for {cmd}  (type HELP)")
