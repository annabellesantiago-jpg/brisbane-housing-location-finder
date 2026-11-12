import logging


def setup_logging(level: str = "INFO") -> None:
    """This is a common function for logging which must be used across all other modules/functions.
    The function is safe to be called twice
    Args:
        level: logging level (INFO, WARNING, ERROR)
    Returns:
        None"""

    logger = logging.getLogger("brisbane_house_finder")
    logger.setLevel(level)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(handler)

    logger.propagate = False
