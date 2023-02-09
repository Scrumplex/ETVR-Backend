from logging import StreamHandler
import logging
import inspect
import sys
from .types import LogLevel
from enum import Enum


def setup_logger() -> None:
    logger = logging.getLogger()
    # TODO: should probably load this from config or have it be set with a parameter
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(levelname)s || %(threadName)s[%(thread)d] --> %(name)s<[%(module)s, %(funcName)s(), %(lineno)d]> :: %(message)s"
    )
    # Create the Handler for logging data to console
    console_handler = StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    # add handlers
    logger.addHandler(console_handler)


def set_log_level(level: LogLevel) -> None:
    logger = logging.getLogger()
    logger.setLevel(level.value)


def get_logger() -> logging.getLogger:
    # get calling module
    frm = inspect.stack()[1]
    caller_module = inspect.getmodule(frm[0]).__name__
    # create logger for caller module
    logger = logging.getLogger(caller_module)
    logger.debug("Initialized logger for %s", caller_module)
    return logger
