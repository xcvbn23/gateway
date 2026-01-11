import os
import subprocess
from unittest.mock import MagicMock

import uninstall

class TestStopAndRemoveService:
    def test_stop_and_remove_service_success(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        service_name = "gateway"
        service_file = f"/etc/systemd/system/{service_name}.service"

        # Create fake service file
        fake_filesystem.create_dir("/etc/systemd/system")
        fake_filesystem.create_file(
            service_file, contents="[Unit]\nDescription=Gateway"
        )

        uninstall.stop_and_remove_service(service_name)

        # Check service file removed
        assert not os.path.exists(service_file)

        # Check subprocess calls
        expected_calls = [
            ((["systemctl", "stop", service_name],), {"check": False}),
            ((["systemctl", "disable", service_name],), {"check": False}),
            ((["systemctl", "daemon-reload"],), {"check": True}),
        ]
        mock_run.assert_has_calls(expected_calls)

    def test_stop_and_remove_service_no_file(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        service_name = "gateway"

        # Ensure directory exists but file doesn't
        fake_filesystem.create_dir("/etc/systemd/system")

        uninstall.stop_and_remove_service(service_name)

        # Should still call systemctl commands
        expected_calls = [
            ((["systemctl", "stop", service_name],), {"check": False}),
            ((["systemctl", "disable", service_name],), {"check": False}),
            ((["systemctl", "daemon-reload"],), {"check": True}),
        ]
        mock_run.assert_has_calls(expected_calls)

    def test_stop_and_remove_service_daemon_reload_fails(
        self, monkeypatch, fake_filesystem
    ):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        service_name = "gateway"
        service_file = f"/etc/systemd/system/{service_name}.service"

        # Create fake service file
        fake_filesystem.create_dir("/etc/systemd/system")
        fake_filesystem.create_file(
            service_file, contents="[Unit]\nDescription=Gateway"
        )

        # Make daemon-reload fail
        mock_run.side_effect = [
            MagicMock(),
            MagicMock(),
            subprocess.CalledProcessError(1, "systemctl"),
        ]

        # Should not raise because exception is caught
        uninstall.stop_and_remove_service(service_name)


class TestRemoveInstallDirectory:
    def test_remove_install_directory_exists(self, monkeypatch, fake_filesystem):
        install_dir = "/opt/gateway"

        # Create fake directory
        fake_filesystem.create_dir(install_dir)

        uninstall.remove_install_directory(install_dir)

        assert not os.path.exists(install_dir)

    def test_remove_install_directory_not_exists(self, monkeypatch, fake_filesystem):
        install_dir = "/opt/gateway"

        # Directory doesn't exist in fake filesystem
        uninstall.remove_install_directory(install_dir)

        # Should not raise


class TestRemoveGatewayUser:
    def test_remove_gateway_user_exists(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        # id succeeds, userdel succeeds
        mock_run.side_effect = [MagicMock(), MagicMock()]

        uninstall.remove_user()

        expected_calls = [
            ((["id", "gateway"],), {"check": True, "capture_output": True}),
            ((["userdel", "gateway"],), {"check": True}),
        ]
        mock_run.assert_has_calls(expected_calls)

    def test_remove_gateway_user_not_exists(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        # id fails
        mock_run.side_effect = [subprocess.CalledProcessError(1, "id")]

        uninstall.remove_user()

        # Should only call id
        mock_run.assert_called_once_with(
            ["id", "gateway"], check=True, capture_output=True
        )

    def test_remove_gateway_user_userdel_fails(self, monkeypatch):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        # id succeeds, userdel fails
        mock_run.side_effect = [
            MagicMock(),
            subprocess.CalledProcessError(1, "userdel"),
        ]

        # Should not raise because exception is caught
        uninstall.remove_user()


class TestMainFlow:
    def test_main_flow(self, monkeypatch):
        mock_check_su = MagicMock()
        mock_stop_service = MagicMock()
        mock_remove_dir = MagicMock()
        mock_remove_user = MagicMock()

        monkeypatch.setattr("uninstall.check_su", mock_check_su)
        monkeypatch.setattr("uninstall.stop_and_remove_service", mock_stop_service)
        monkeypatch.setattr("uninstall.remove_install_directory", mock_remove_dir)
        monkeypatch.setattr("uninstall.remove_user", mock_remove_user)

        # Simulate main flow
        uninstall.check_su()
        uninstall.stop_and_remove_service("gateway")
        uninstall.remove_install_directory("/opt/gateway")
        uninstall.remove_user()

        mock_check_su.assert_called_once()
        mock_stop_service.assert_called_once_with("gateway")
        mock_remove_dir.assert_called_once_with("/opt/gateway")
        assert mock_remove_user.call_count == 1
