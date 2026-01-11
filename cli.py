#!/usr/bin/env python3

import argparse
import asyncio
import grp
import os
import pwd
import sys

from pydantic import ValidationError

from custom_logging import logger
from gateway import TCPProxy
from tcp_proxy_settings import TCPProxySettings


def main():
    parser = argparse.ArgumentParser(description="Gateway")
    parser.add_argument(
        "--listen-address",
        dest="listen_address",
        default="127.0.0.1",
        help="Address to listen on (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--target-address",
        dest="target_address",
        default="127.0.0.1",
        help="Target address to forward to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--target-port",
        type=int,
        default=80,
        help="Target port to forward to (default: 80)",
    )
    parser.add_argument(
        "--pushgateway-url",
        help="Prometheus pushgateway URL (e.g., http://localhost:9091)",
    )
    parser.add_argument(
        "--user", help="User to drop privileges to after binding (for ports < 1024)"
    )
    parser.add_argument(
        "--group", help="Group to drop privileges to after binding (for ports < 1024)"
    )

    args = parser.parse_args()

    logger.debug("Validating configuration")
    try:
        config = TCPProxySettings(**vars(args))
    except ValidationError as e:
        logger.error(f"Configuration validation error: {e}")
        sys.exit(1)
    logger.debug("Configuration validated successfully")

    old_uid = os.getuid()
    current_user = pwd.getpwuid(old_uid).pw_name
    old_gid = os.getgid()
    current_group = grp.getgrgid(old_gid).gr_name
    logger.info(f"Initialised as user {current_user}:{old_uid}")
    logger.info(f"Initialised as group {current_group}:{old_gid}")

    proxy = TCPProxy(config)

    async def _run_with_handler():
        loop = asyncio.get_running_loop()

        def _handle_loop_exception(loop, context):
            msg = context.get("message") or context
            exc = context.get("exception")
            logger.error(f"Unhandled exception in event loop: {msg}", exc_info=exc)

        loop.set_exception_handler(_handle_loop_exception)
        await proxy.start()

    try:
        asyncio.run(_run_with_handler())
    except KeyboardInterrupt:
        logger.info("\nGateway stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
