import subprocess
from unittest.mock import MagicMock

import pytest

from utils import create_user


class TestCreateUser:
    def test_successful(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "id"),
            MagicMock(),
        ]  # id fails, useradd succeeds
        create_user()
        assert mock_run.call_count == 2
        mock_run.assert_any_call(["id", "gateway"], check=True, capture_output=True)
        mock_run.assert_any_call(
            [
                "useradd",
                "--system",
                "--shell",
                "/usr/sbin/nologin",
                "--home",
                "/opt/gateway",
                "--create-home",
                "gateway",
            ],
            check=True,
        )

    def test_user_exists(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        mock_run.side_effect = [MagicMock()]  # id command succeeds
        create_user()
        mock_run.assert_called_once_with(
            ["id", "gateway"], check=True, capture_output=True
        )

    def test_handle_failed_useradd_fails(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "id"),
            subprocess.CalledProcessError(1, "useradd"),
        ]
        with pytest.raises(subprocess.CalledProcessError):
            create_user()

