# -*- coding: utf-8 -*-
"""
Example scheme for a task.
"""


import logging

from pyleco.utils.message_handler import MessageHandler


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Handler(MessageHandler):
    def handle_command(self, command, content=None):
        print(command, content)
        return ["A"]


def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    c = Handler("printer")

    # Continuous loop
    c.listen(stop_event)

    # Finish


if __name__ == "__main__":
    # Run the task if executed.
    class Signal:
        def is_set(self):
            return False
    try:
        task(Signal())
    except KeyboardInterrupt:
        pass
