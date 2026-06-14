"""
Playwright configuration for E2E tests.
"""

import pytest


def pytest_configure(config):
    """Configure pytest with Playwright settings."""
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }
