import logging


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the brisbane_house_finder package.

    Adds one stream handler to the package logger with the format
    "time | level | logger name | message". The root logger is not changed,
    and log lines are not passed up to it. Safe to call more than once: a
    second call updates the level but does not add another handler.

    Args:
        level: Minimum level to show: "DEBUG", "INFO", "WARNING" or "ERROR".
    """

    logger = logging.getLogger("brisbane_house_finder")
    logger.setLevel(level)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(handler)

    logger.propagate = False
