"""
Pytest configuration for the Univa backend test suite.

This file is intentionally minimal at this stage.

Project-wide fixtures and pytest configuration should only be added

when an actual test requirement identifies the need for them.

"""

import pytest


@pytest.fixture
def test_marker():
    """Simple fixture used to verify pytest fixture discovery."""
    return True