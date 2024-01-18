# -*- coding: utf-8 -*-
"""
Example scheme for a task. 'task'
"""
# TODO write the task description in the docstring and state the Component name, if applicable.


import logging

from pyleco.utils.data_publisher import DataPublisher
from pyleco.utils.timers import SignallingTimer


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Parameters
interval = 0.05  # Readout interval in s


# TODO adjust this task formular according to your needs.
def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    # TODO call initialization you may use timers.RepeatingTimer or SignallingTimer
    publisher = DataPublisher(full_name="topic", log=log)
    t = SignallingTimer(interval)
    t.start()

    # Continuos loop
    # TODO choose one of these three:
    while not stop_event.is_set():
        # continuous loop: for example reading zmq communication
        pass  # TODO replace with content.

    while not stop_event.wait(1):  # as an alternative to sleep(1)
        # wait a second and repeat the following lines. if stopped, leave loop
        pass  # Just waiting for a stop signal
        publisher.send_data(data={'test': .03})

    while not stop_event.is_set():
        # Waiting on a timer timeout
        if t.signal.wait(0.5):
            pass  # TODO replace with readout

    # Finish
    # TODO finish the device gracefully
    t.cancel()  # Stop timer


# TODO this is a manual example, remove as desired.
# from time import perf_counter, sleep
# def example_task(stop_event):  # noqa: E302
#     """Example how a task could look like."""
#     # Initialize
#     publisher = intercom.Publisher(log=log)
#     log.info("Test task started.")
#     t = timers.SignallingTimer(interval)
#     t.start()
#     now = perf_counter()
#     while not stop_event.is_set():
#         if t.signal.wait(1):
#             # use the timer to just indicate the timeout.
#             n2 = perf_counter()
#             print(n2 - now)
#             now = n2
#             sleep(.001)
#             # signal.clear()
#             publisher({'test': .03})
#     # Finish
#     t.cancel()
#     log.info("Test task stopped")


# TODO this is an actor example, remove as desired.
# def task(stop_event):
#     """The task which is run by the starter."""
#     # Initialize
#     with Actor("innolas", RockFiberLaser, periodic_reading=interval) as actor:
#         actor.connect(com)

#         # Continuos loop
#         actor.listen(stop_event=stop_event)

#         # Finish
#         # in listen and __exit__ included


if __name__ == "__main__":
    """Run the task if the module is executed."""
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

    class Signal:
        def is_set(self):
            return False
    try:
        task(Signal())
    except KeyboardInterrupt:
        pass
