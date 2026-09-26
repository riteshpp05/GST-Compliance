#!/usr/bin/env python3
"""
Test Suite Runner for UC15 GST Compliance Agent.
Executes:
  1. Unit Tests (models, rules, normalization, engines)
  2. Integration Tests (end-to-end pipeline)
  3. Regression Tests (legacy test_scoring.py)
"""
from __future__ import annotations

import os
import sys
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def main() -> int:
    print("\n" + "=" * 70)
    print("  UC15 GST COMPLIANCE INTELLIGENCE AGENT — SPRINT 1–3 TEST SUITE")
    print("=" * 70)


    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 1. Discover unit tests
    unit_dir = os.path.join(REPO_ROOT, "tests", "unit")
    if os.path.exists(unit_dir):
        suite.addTests(loader.discover(start_dir=unit_dir, pattern="test_*.py"))

    # 2. Discover integration tests
    integration_dir = os.path.join(REPO_ROOT, "tests", "integration")
    if os.path.exists(integration_dir):
        suite.addTests(loader.discover(start_dir=integration_dir, pattern="test_*.py"))

    # Run discovered tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if not result.wasSuccessful():
        print(f"  Unit/Integration Failures ({len(result.failures)}):")
        for f in result.failures:
            print(f"    - {f[0]}: {f[1].splitlines()[-1]}")
        print(f"  Unit/Integration Errors ({len(result.errors)}):")
        for e in result.errors:
            print(f"    - {e[0]}: {e[1].splitlines()[-1]}")

    overall_ok = result.wasSuccessful()
    if overall_ok:
        print("  ALL TESTS PASSED SUCCESSFULLY (Unit & Integration)")
    else:
        print("  SOME TESTS FAILED!")
    print("=" * 70 + "\n")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
