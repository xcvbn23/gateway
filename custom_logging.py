import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from systemd.journal import JournalHandler

    handler = JournalHandler()
except ImportError:
    logger.debug("systemd.journal not available, using StreamHandler for logging.")
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

logger.addHandler(handler)
