import pytest


@pytest.fixture
def fake_filesystem(fs):
    yield fs
