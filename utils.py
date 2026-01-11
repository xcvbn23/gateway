import os
import subprocess
import sys

from custom_logging import logger
from settings import INSTALL_DIR, USER


def check_su():
    logger.debug("Checking for su privileges.")
    if os.geteuid() != 0:
        logger.error("This script must be run with su privileges.")
        sys.exit(1)
    else:
        logger.debug("su privileges confirmed.")


def create_user():
    logger.debug("Creating user '%s'.", USER)

    try:
        subprocess.run(["id", USER], check=True, capture_output=True)
        logger.debug("User '%s' already exists.", USER)
    except subprocess.CalledProcessError:
        subprocess.run(
            [
                "useradd",
                "--system",
                "--shell",
                "/usr/sbin/nologin",
                "--home",
                INSTALL_DIR,
                "--create-home",
                USER,
            ],
            check=True,
        )
        logger.debug("User '%s' created", USER)
