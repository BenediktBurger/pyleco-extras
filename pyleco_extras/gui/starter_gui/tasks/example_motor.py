# -*- coding: utf-8 -*-
"""
Example for a motor controller task simulating a TMC motor card. 'example_motor'
"""
# TODO write the task description in the docstring and state the Component name.


import logging

from pyleco_extras.actors.tmc_motor_actor import TMCMotorActor

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Parameters
configs = [  # The configuration dictionaries
    {'motorNumber': 0,
     'maxCurrent': 50,
     'standbyCurrent': 5,
     'positioningSpeed': 512,
     'acceleration': 512,
     'stepResolution': 3,
     'stepCount': 200,
     'unitSize': 360,
     'unitSymbol': "°",
     'unitOffset': 0,
     'stallguardThreshold': 0,
     },
    {'motorNumber': 1,
     'maxCurrent': 50,
     'standbyCurrent': 5,
     'positioningSpeed': 512,
     'acceleration': 512,
     'stepResolution': 3,
     'stepCount': 200,
     'unitSize': 200,
     'unitSymbol': " fs",
     'unitOffset': 0,
     'stallguardThreshold': 0,
     },
]
# Dictionary with names for the motors
motorDict = {
    'motor0': 0,
    'testing': 1
}
# Name to communicate with
name = "example_motor"
# Name of the card or COM port
card = 5


def task(stop_event):
    """The task which is run by the starter."""
    # Initialize
    try:
        actor = TMCMotorActor(name, card, motorDict, log=log)
    except Exception as exc:
        log.exception(f"Creation of {name} at card {card} failed.", exc_info=exc)
        return
    for config in configs:
        actor.configure_motor(config)

    log.debug("Motor configured.")
    # Continuous loop
    actor.listen(stop_event)

    # Finish
    actor.disconnect()
    actor.close()


if __name__ == "__main__":
    # Run the task if executed.
    class Signal:
        def is_set(self):
            return False
    try:
        task(Signal())
    except KeyboardInterrupt:
        pass
