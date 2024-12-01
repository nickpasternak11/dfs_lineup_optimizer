import logging
from datetime import datetime
import pytz

class ESTFormatter(logging.Formatter):
    """Custom logging formatter to use Eastern Time for timestamps."""
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.est_tz = pytz.timezone('America/New_York')

    def formatTime(self, record, datefmt=None):
        # Convert the timestamp to a datetime object in EST
        dt = datetime.fromtimestamp(record.created, self.est_tz)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
        return s

formatter = ESTFormatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger("orchestrator")
log.setLevel(logging.INFO)
log.addHandler(handler)
