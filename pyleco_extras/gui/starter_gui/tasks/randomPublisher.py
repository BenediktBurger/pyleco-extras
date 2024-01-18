# -*- coding: utf-8 -*-
"""
For testing devices publish random values.

Created on Sat Jul  2 06:25:50 2022 by Benedikt Moneke
"""

from random import random
import sys

from devices import intercom

standalone = False
interval = 0.1


def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    kwargs = {}
    if standalone:
        kwargs['port'] = 11099
        kwargs['standalone'] = standalone
    publisher = intercom.Publisher(**kwargs)

    while not stop_event.wait(interval):  # as an alternative to sleep(1)
        # wait a second and repeat the following lines. if stopped, leave loop
        publisher({'random': random()})
