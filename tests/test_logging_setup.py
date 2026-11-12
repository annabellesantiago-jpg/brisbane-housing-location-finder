import logging

import pytest

from brisbane_house_finder.logging_setup import setup_logging


@pytest.fixture(autouse=True)
def reset_logger():
    logger = logging.getLogger("brisbane_house_finder")
    logger.handlers.clear()
    logger.propagate = True
    yield
    logger.handlers.clear()
    logger.propagate = True


def test_sets_level():
    setup_logging("DEBUG")
    logger = logging.getLogger("brisbane_house_finder")
    assert logger.level == logging.DEBUG


def test_no_duplicate_handlers():
    setup_logging("DEBUG")
    setup_logging("INFO")
    logger = logging.getLogger("brisbane_house_finder")
    assert len(logger.handlers) == 1


def test_does_not_propagate():
    setup_logging("INFO")
    logger = logging.getLogger("brisbane_house_finder")
    assert logger.propagate is False
