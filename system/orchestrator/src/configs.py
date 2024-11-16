import logging

# class Formatter(logging.Formatter):
#     """override logging.Formatter to use an aware datetime object"""
#     def converter(self, timestamp):
#         dt = datetime.datetime.fromtimestamp(timestamp)
#         tzinfo = pytz.timezone('America/New York')
#         return tzinfo.localize(dt)
        
#     def formatTime(self, record, datefmt=None):
#         dt = self.converter(record.created)
#         if datefmt:
#             s = dt.strftime(datefmt)
#         else:
#             try:
#                 s = dt.isoformat(timespec='milliseconds')
#             except TypeError:
#                 s = dt.isoformat()
#         return s

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
log = logging.getLogger("orchestrator")
