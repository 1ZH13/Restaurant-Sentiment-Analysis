"""
Playwright-specific configuration for E2E tests.
"""

import pytest
from pathlib import Path

# Ensure project root is in path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "e2e: end-to-end tests using Playwright")
