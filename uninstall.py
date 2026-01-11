import os
import shutil
import subprocess

from custom_logging import logger

from settings import INSTALL_DIR, USER
from utils import check_su

service_name = "gateway"


def stop_and_remove_service(service_name):
    """Stop, disable and remove the systemd service"""
    try:
        logger.info("Stopping '%s' service...", service_name)
        subprocess.run(["systemctl", "stop", service_name], check=False)
        logger.info("Disabling '%s' service...", service_name)
        subprocess.run(["systemctl", "disable", service_name], check=False)

        service_file = f"/etc/systemd/system/{service_name}.service"
        if os.path.exists(service_file):
            os.remove(service_file)
            logger.info("Removed service file: %s", service_file)
        else:
            logger.info("Service file not found: %s", service_file)

        # Reload daemon
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        logger.info("Systemd daemon reloaded.")

    except Exception as e:
        logger.error("Error removing service: %s", e)


def remove_install_directory(install_dir: str):
    """Remove the installation directory"""
    if os.path.exists(install_dir):
        shutil.rmtree(install_dir)
        logger.info("Removed installation directory: %s", install_dir)
    else:
        logger.info("Installation directory not found: %s", install_dir)

def remove_user():
    """Remove the user and group"""
    try:
        # Check if user exists
        subprocess.run(["id", USER], check=True, capture_output=True)
        logger.info("Removing '%s' user...", USER)
        subprocess.run(["userdel", USER], check=True)
        logger.info("User removed")
    except subprocess.CalledProcessError:
        logger.info("User does not exist")

if __name__ == "__main__":
    check_su()

    # Stop and remove service
    stop_and_remove_service(service_name)

    remove_install_directory(INSTALL_DIR)

    remove_user()

    logger.info("Uninstallation completed.")
