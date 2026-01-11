import os
import shutil
import subprocess
import sys

from custom_logging import logger
from settings import GROUP, INSTALL_DIR, SYSTEMD_UNIT_DIR, USER
from utils import check_su, create_user


def copy_source_files(source_files, install_dir):
    os.makedirs(install_dir, exist_ok=True)
    logger.debug("Created install directory '%s' if it did not exist.", install_dir)
    subprocess.run(["chown", f"{USER}:{GROUP}", install_dir], check=True)

    # Copy each source file
    for source_file in source_files:
        if not os.path.exists(source_file):
            logger.warning("Source file '%s' not found, skipping.", source_file)
            continue

        # Get just the filename for destination
        dest_file = os.path.join(install_dir, os.path.basename(source_file))
        shutil.copy2(source_file, dest_file)
        logger.debug("Gateway code copied to '%s'", dest_file)

        # Change ownership of the file
        subprocess.run(["chown", f"{USER}:{GROUP}", dest_file], check=True)

        # Make it executable if it's a Python file
        if source_file.endswith(".py"):
            os.chmod(dest_file, 0o755)
            logger.debug("Set executable permissions on '%s'", dest_file)

def create_virtual_environment(install_dir):
    venv_dir = os.path.join(install_dir, ".venv")
    logger.debug("Creating virtual environment in '%s'", venv_dir)
    
    # Create virtual environment
    subprocess.run(["python3", "-m", "venv", venv_dir], check=True)
    
    # Install dependencies using pip
    pip_path = os.path.join(venv_dir, "bin", "pip")
    logger.debug("Installing dependencies with pip")
    subprocess.run([pip_path, "install", "-e", install_dir], check=True)
    
    # Change ownership of venv
    subprocess.run(["chown", "-R", f"{USER}:{GROUP}", venv_dir], check=True)
    logger.debug("Virtual environment created and dependencies installed")


def install_systemd_unit(unit_file: str, service_name: str):
    unit_file_path = os.path.join(SYSTEMD_UNIT_DIR, f"{service_name}.service")
    logger.debug("Installing systemd unit file to '%s'.", unit_file_path)

    # Copy the unit file, overwriting if it exists
    if os.path.exists(unit_file):
        logger.debug("Copying unit file from '%s' to '%s'.", unit_file, unit_file_path)
        shutil.copy2(unit_file, unit_file_path)
        logger.debug("Unit file copied to '%s'.", unit_file_path)

        # Reload daemon
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        logger.debug("Systemd daemon reloaded.")

        subprocess.run(["systemctl", "enable", service_name], check=True)
        logger.debug("Systemd service '%s' enabled.", service_name)

        subprocess.run(["systemctl", "start", service_name], check=True)
        logger.debug("Systemd service '%s' started.", service_name)
    else:
        logger.warning("Unit file '%s' not found.", unit_file)
        sys.exit(1)
    


def main():
    check_su()

    create_user()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_copy = [
        "cli.py",
        "custom_logging.py",
        "gateway.py",
        "pyproject.toml",
        "README.md",
        "settings.py",
        "tcp_proxy_settings.py",
        "utils.py"
    ]
    source_files = [
        os.path.join(script_dir, filename) for filename in files_to_copy
    ]

    # Install gateway code
    copy_source_files(source_files, INSTALL_DIR)

    # Create virtual environment and install dependencies
    create_virtual_environment(INSTALL_DIR)

    # Install systemd unit
    unit_file = os.path.join(script_dir, "gateway.service")
    service_name = "gateway"

    install_systemd_unit(unit_file, service_name)


if __name__ == "__main__":
    main()
