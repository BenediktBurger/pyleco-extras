#
# This file is part of the PyLECO package.
#
# Copyright (c) 2023-2024 PyLECO Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
from threading import Event
from typing import Any, Callable, Optional

import zmq

from ..core import PROXY_SENDING_PORT
from .extended_message_handler import ExtendedMessageHandler
from .data_publisher import DataPublisher


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Republisher(ExtendedMessageHandler):
    """Listen on some values and republish a modified version.

    Call `listener.start_listen()` to actually listen.

    Republish values under a new name after having modified them.
    Time delay is around 1-2 ms.

    :param dict handlings: Dictionary with tuples of callable and new name.

    The following example takes the values of key 'old' and publishes the square
    of that value under the key 'new'. Wait until a KeyboardInterrupt (Ctrl+C) happens.

    .. code-block:: python

        def square(value):
            return value ** 2
        republisher = Republisher(handlings={'old': (square, "new")})
        republisher.start_listen()
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
    """

    handlings: dict[str, tuple[Callable[[Any], Any], str]]

    def __init__(self, name: str = "Republisher",
                 handlings: Optional[dict[str, tuple[Callable[[Any], Any], str]]] = None,
                 data_port: int = PROXY_SENDING_PORT,
                 context: Optional[zmq.Context] = None,
                 **kwargs):
        context = zmq.Context.instance() if context is None else context
        super().__init__(name, data_port=data_port, context=context, **kwargs)
        self.publisher = DataPublisher(name, context=context)
        self.handlings = {} if handlings is None else handlings

    def start_listen(self, stop_event: Optional[Event] = None) -> None:
        if stop_event is None:
            self.listen()
        else:
            self.listen(stop_event=stop_event)

    def _listen_setup(self, **kwargs) -> zmq.Poller:
        poller = super()._listen_setup(**kwargs)
        for key in self.handlings.keys():
            self.subscribe(key)
        return poller

    def handle_subscription_data(self, data: dict[str, Any]) -> None:
        """Call a calibration method and publish data under a new name."""
        new = self.calculate_new_data(data=data)
        if new:
            self.publish_new_data(data=new)

    def calculate_new_data(self, data: dict[str, Any]) -> dict[str, Any]:
        new: dict[str, Any] = {}
        if not isinstance(data, dict):
            log.error(f"{data} received, which is not a dictionary.")
        for key, value in data.items():
            if handling := self.handlings.get(key):
                try:
                    new[handling[1]] = handling[0](value)
                except Exception:
                    log.exception(f"Handling of '{key}' failed.")
        return new

    def publish_new_data(self, data: dict[str, Any]) -> None:
        self.publisher.send_legacy(data=data)
