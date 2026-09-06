from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """
    :return: путь к папке с данными для тестов, под которые они написаны
    """
    return Path(__file__).parent / "test_data"
