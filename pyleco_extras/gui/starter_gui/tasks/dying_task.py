# -*- coding: utf-8 -*-
"""
Stops after some time
"""

import time
import logging


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Parameters
interval = 5  # Readout interval in s


def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    log.info("dying task started.")
    time.sleep(interval)
    log.info("dying task stopped.")


if __name__ == "__main__":
    # Run the task if executed.
    class Signal:
        def is_set(self):
            return False
    try:
        task(Signal())
    except KeyboardInterrupt:
        pass
