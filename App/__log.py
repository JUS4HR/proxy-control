import logging
import logging.handlers

from . import __utils as _u

LOG_FILE = _u.getExeRelPath("app.log")


def debug(msg):
    _logger.debug(msg)


def info(msg):
    _logger.info(msg)


def warning(msg):
    _logger.warning(msg)


def error(msg):
    _logger.error(msg)


_logger = logging.getLogger("ladder")

_formatter = logging.Formatter("%(asctime)s %(levelname)s\t%(message)s")

_stream_handler = logging.StreamHandler()
_rotating_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=1024 * 1024, backupCount=5
)
_stream_handler.setFormatter(_formatter)
_rotating_file_handler.setFormatter(_formatter)
_stream_handler.setLevel(logging.DEBUG)
_rotating_file_handler.setLevel(logging.DEBUG)
_logger.addHandler(_stream_handler)
_logger.addHandler(_rotating_file_handler)
_logger.setLevel(logging.DEBUG)
