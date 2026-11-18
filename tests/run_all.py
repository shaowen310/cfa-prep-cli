"""
CFA Prep CLI - Standalone test runner
Author: CodeBuddy AI Assistant
Purpose: Run every test function of the tests/ package without pytest.

Usage:
    python tests/run_all.py
    python -m tests.run_all
"""

import importlib
import pkgutil
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import cast

# Add the project root to the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _iter_test_modules():
    """Yield the imported test modules of the tests/ package"""
    import tests

    for module_info in pkgutil.iter_modules(tests.__path__):
        if not module_info.name.startswith("test_"):
            continue
        yield importlib.import_module(f"tests.{module_info.name}")


def run_all_tests() -> int:
    """Run every test function and print the results"""
    passed = 0
    failed = 0
    total = 0
    failures: list[tuple[str, str, str]] = []

    print("=" * 60)
    print("CFA Prep CLI - Running the test suite")
    print("=" * 60)

    for module in _iter_test_modules():
        module_name = module.__name__.replace("tests.", "")
        print(f"\n📦 {module_name}")

        test_names = sorted(
            name for name in dir(module)
            if name.startswith("test_")
            and callable(cast(object, getattr(module, name, None)))
        )

        for name in test_names:
            total += 1
            test_func = cast(Callable[[], None], getattr(module, name))
            try:
                test_func()
            except Exception:  # noqa: BLE001 - a failing test must not stop the run
                failed += 1
                failures.append((module_name, name, traceback.format_exc()))
                print(f"  ❌ {name}")
            else:
                passed += 1
                print(f"  ✅ {name}")

    print("\n" + "=" * 60)
    for module_name, name, error in failures:
        print(f"\n❌ {module_name}.{name}\n{error}")

    print(f"\nTest results: {passed} passed / {failed} failed / {total} total")
    print("=" * 60)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
