# -*- coding: utf-8 -*-
"""
Simulate an instrument controller for a fantasy instrument.
"""


import logging
from random import random
import time

from pymeasure.instruments import Instrument
from pymeasure.adapters import ProtocolAdapter

from devices import controller


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Parameters
interval = 0.5  # Readout interval in s


class FantasyInstrument(Instrument):

    def __init__(self, adapter, name="stuff", *args, **kwargs):
        super().__init__(ProtocolAdapter(), name, includeSCPI=False)
        self._prop = 5
        self._prop2 = 7

    @property
    def prop(self):
        return self._prop

    @prop.setter
    def prop(self, value):
        self._prop = value

    @property
    def prop2(self):
        return self._prop2

    @prop2.setter
    def prop2(self, value):
        self._prop2 = value

    def silent_method(self, value):
        self._method_value = value

    def returning_method(self, value):
        return value ** 2

    @property
    def long(self):
        time.sleep(0.5)
        return 7

    @property
    def random(self):
        return random()


def readout(device, publisher):
    publisher({'instrument': device.random})


def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    c = controller.InstrumentController("instrument", FantasyInstrument, periodic_reading=interval,
                                        auto_connect={'adapter': True})
    c._readout = readout
    c.start_timer()

    # Continuos loop
    c.listen(stop_event)


if __name__ == "__main__":
    # Run the task if executed.
    class Signal:
        def is_set(self):
            return False
    try:
        task(Signal())
    except KeyboardInterrupt:
        pass
