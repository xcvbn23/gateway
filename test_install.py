import os
import pytest
import subprocess
from unittest.mock import MagicMock
import install


class TestInstallSourceFiles:
    def test_install_source_files(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        source_files = ["/fake/source/cli.py"]
        install_dir = "/opt/gateway"
        dest_file = os.path.join(install_dir, "cli.py")

        # Create fake source file
        fake_filesystem.create_file(source_files[0], contents="fake code")

        install.copy_source_files(source_files, install_dir)

        # Check file copied and permissions
        assert os.path.exists(dest_file)
        assert os.stat(dest_file).st_mode & 0o755 == 0o755

        # Check subprocess calls for chown
        expected_calls = [
            ((["chown", "gateway:gateway", install_dir],), {"check": True}),
            ((["chown", "gateway:gateway", dest_file],), {"check": True}),
        ]
        mock_run.assert_has_calls(expected_calls, any_order=True)

    def test_source_files_chown_fails(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        source_files = ["/fake/source/cli.py"]
        install_dir = "/opt/gateway"

        # Create fake source file
        fake_filesystem.create_file(source_files[0], contents="fake code")

        mock_run.side_effect = subprocess.CalledProcessError(1, "chown")
        with pytest.raises(subprocess.CalledProcessError):
            install.copy_source_files(source_files, install_dir)


class TestInstallSystemdUnit:
    def test_install_success(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        unit_file = "/fake/gateway.service"
        service_name = "gateway"
        unit_path = f"/etc/systemd/system/{service_name}.service"

        # Create fake directories and unit file
        fake_filesystem.create_dir("/etc/systemd/system")
        fake_filesystem.create_file(unit_file, contents="[Unit]\nDescription=Gateway")

        install.install_systemd_unit(unit_file, service_name)

        assert os.path.exists(unit_path)
        expected_calls = [
            ((["systemctl", "daemon-reload"],), {"check": True}),
            ((["systemctl", "enable", service_name],), {"check": True}),
            ((["systemctl", "start", service_name],), {"check": True}),
        ]
        mock_run.assert_has_calls(expected_calls)

    def test_install_missing_file(self, monkeypatch):
        mock_exit = MagicMock()
        mock_run = MagicMock()
        monkeypatch.setattr("sys.exit", mock_exit)
        monkeypatch.setattr("subprocess.run", mock_run)

        unit_file = "/fake/missing.service"
        service_name = "gateway"

        install.install_systemd_unit(unit_file, service_name)
        mock_exit.assert_called_once_with(1)
        mock_run.assert_not_called()

    def test_install_daemon_reload_fails(self, monkeypatch, fake_filesystem):
        mock_run = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_run)

        unit_file = "/fake/gateway.service"
        service_name = "gateway"

        # Create fake directories and unit file
        fake_filesystem.create_dir("/etc/systemd/system")
        fake_filesystem.create_file(unit_file, contents="[Unit]\nDescription=Gateway")

        mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")
        with pytest.raises(subprocess.CalledProcessError):
            install.install_systemd_unit(unit_file, service_name)


class TestMainFlow:
    def test_main_flow(self, monkeypatch):
        mock_check_su = MagicMock()
        mock_create_user = MagicMock()
        mock_install_code = MagicMock()
        mock_create_venv = MagicMock()
        mock_install_unit = MagicMock()
        mock_dirname = MagicMock()
        mock_join = MagicMock()

        monkeypatch.setattr("install.check_su", mock_check_su)
        monkeypatch.setattr("install.create_user", mock_create_user)
        monkeypatch.setattr("install.copy_source_files", mock_install_code)
        monkeypatch.setattr("install.create_virtual_environment", mock_create_venv)
        monkeypatch.setattr("install.install_systemd_unit", mock_install_unit)
        monkeypatch.setattr("os.path.dirname", mock_dirname)
        monkeypatch.setattr("os.path.join", mock_join)

        mock_dirname.return_value = "/fake"
        mock_join.side_effect = lambda *args: "/".join(args)

        install.main()

        mock_check_su.assert_called_once()
        mock_create_user.assert_called_once()
        mock_install_code.assert_called_once_with(
            [
                "/fake/cli.py",
                "/fake/custom_logging.py",
                "/fake/gateway.py",
                "/fake/pyproject.toml",
                "/fake/README.md",
                "/fake/settings.py",
                "/fake/tcp_proxy_settings.py",
                "/fake/utils.py",
            ],
            "/opt/gateway",
        )
        mock_create_venv.assert_called_once_with("/opt/gateway")
        mock_install_unit.assert_called_once_with("/fake/gateway.service", "gateway")
