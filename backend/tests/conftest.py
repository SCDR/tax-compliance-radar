from __future__ import annotations

import pytest

from tax_compliance_radar import testing_config


@pytest.fixture()
def test_settings():
    return testing_config.TEST_SETTINGS
