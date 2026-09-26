import logging
from datetime import datetime

import pytz

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ESTFormatter(logging.Formatter):
    """Custom logging formatter to use Eastern Time for timestamps."""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.est_tz = pytz.timezone("America/New_York")

    def formatTime(self, record, datefmt=None):
        # Convert the timestamp to a datetime object in EST
        dt = datetime.fromtimestamp(record.created, self.est_tz)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s


def get_logger(name: str) -> logging.Logger:
    """Return an INFO logger that writes Eastern-time lines to stderr."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Called at import time from several modules; attach the handler once.
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ESTFormatter(fmt=FORMAT))
        logger.addHandler(handler)
    return logger
