import logging


class MobileRequestFilter(logging.Filter):
    def filter(self, record):
        # Check if this is a mobile request
        if hasattr(record, 'platform'):
            return True
        return False