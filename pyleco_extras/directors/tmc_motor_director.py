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
from typing import Any, Optional, Union

from pytrinamic.modules import TMCM6110  # type: ignore

from pyleco.directors.director import Director


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TMCMotorDirector(Director):
    """Direct a Trinamic TMC stepper motor card, corresponding to the `TMCMotorActor`.

    :param str actor: Name of the card actor.
    :param int motor_count: Number of motor connections.
    """

    def __init__(self, actor: Union[bytes, str], motor_count: int = 6, communicator=None,
                 **kwargs) -> None:
        self.motors = [self.Motor(parent=self, number=i) for i in range(motor_count)]
        super().__init__(actor=actor, communicator=communicator, **kwargs)

    class Motor:
        """Simulating a real motor as a drop in replacement for a motor card."""

        def __init__(self, parent: "TMCMotorDirector", number: int) -> None:
            self.parent: TMCMotorDirector = parent
            self.number = number

        AP = TMCM6110._MotorTypeA.AP

        def get_axis_parameter(self, ap_type: int, signed: bool = False) -> Any:
            return self.parent.get_axis_parameter(ap_type, self.number, signed=signed)

        def set_axis_parameter(self, ap_type: int, value) -> None:
            self.parent.set_axis_parameter(ap_type, self.number, value)

        @property
        def actual_position(self) -> int:
            return self.parent.get_actual_position(self.number)

        @actual_position.setter
        def actual_position(self, steps: int) -> None:
            self.parent.set_actual_position(self.number, steps)

        @property
        def actual_velocity(self) -> int:
            return self.parent.get_actual_velocity(self.number)

        def rotate(self, velocity: int) -> None:
            self.parent.rotate(self.number, velocity)

        def stop(self) -> None:
            self.parent.stop(self.number)

        def move_by(self, difference: int, velocity: Optional[int] = None) -> None:
            self.parent.move_by(self.number, difference, velocity=velocity)

        def move_to(self, position: int, velocity: Optional[int] = None) -> None:
            self.parent.move_to(self.number, position, velocity)

        def get_position_reached(self) -> bool:
            return self.parent.get_position_reached(self.number)

    # General methods
    def disconnect(self) -> None:
        """Disconnect the card."""
        return self.call_action("disconnect")

    def configure_motor(self, config: dict[str, Any]) -> None:
        """Configure a motor according to the dictionary."""
        return self.call_action("configure_motor", config)

    def get_configuration(self, motor: Union[int, str]) -> dict[str, Any]:
        """Get the configuration of `motor`."""
        return self.call_action("get_configuration", motor)

    def get_global_parameter(self, gp_type: int, bank: int, signed: bool = False) -> Any:
        return self.call_action("get_global_parameter", gp_type, bank, signed)

    def set_global_parameter(self, gp_type: int, bank: int, value) -> None:
        return self.call_action("set_global_parameter", gp_type, bank, value)

    def get_axis_parameter(self, ap_type: int, axis: int, signed: bool = False) -> Any:
        return self.call_action("get_axis_parameter", ap_type, axis, signed)

    def set_axis_parameter(self, ap_type: int, axis: int, value) -> None:
        return self.call_action("set_axis_parameter", ap_type, axis, value)

    # Motor controls
    def stop(self, motor: Union[int, str]) -> None:
        """Stop a motor."""
        return self.call_action("stop", motor)

    def get_actual_velocity(self, motor: Union[int, str]) -> int:
        """Get the current velocity of the motor."""
        return self.call_action("get_actual_velocity", motor)

    def get_actual_position(self, motor: Union[int, str]) -> int:
        """Get the current position of the motor."""
        return self.call_action("get_actual_position", motor)

    def get_actual_units(self, motor: Union[int, str]) -> float:
        """Get the actual position in units."""
        return self.call_action("get_actual_units", motor)

    def set_actual_position(self, motor: Union[int, str], steps: int) -> None:
        """Set the current position in steps."""
        return self.call_action("set_actual_position", motor, steps)

    def move_to(self, motor: Union[int, str], position: int, velocity: Optional[int] = None
                ) -> None:
        """Move to a specific position."""
        if velocity is None:
            return self.call_action("move_to", motor, position)
        else:
            return self.call_action("move_to", motor, position, velocity)

    def move_to_units(self, motor: Union[int, str], position: float, velocity: Optional[int] = None
                      ) -> None:
        """Move to a specific position in units."""
        if velocity is None:
            return self.call_action("move_to_units", motor, position)
        else:
            return self.call_action("move_to_units", motor, position, velocity)

    def move_by(self, motor: Union[int, str], difference: int, velocity: Optional[int] = None
                ) -> None:
        """Move to a specific position."""
        if velocity is None:
            return self.call_action("move_by", motor, difference)
        else:
            return self.call_action("move_by", motor, difference, velocity)

    def move_by_units(self, motor: Union[int, str], difference: float,
                      velocity: Optional[int] = None
                      ) -> None:
        """Move to a specific position."""
        if velocity is None:
            return self.call_action("move_by_units", motor, difference)
        else:
            return self.call_action("move_by_units", motor, difference, velocity)

    def rotate(self, motor: Union[int, str], velocity: int) -> None:
        """Rotate the motor with a specific velocity."""
        return self.call_action("rotate", motor, velocity)

    def get_position_reached(self, motor: Union[int, str]) -> bool:
        """Get whether the motor reached its position."""
        return self.call_action("get_position_reached", motor)

    def get_motor_dict(self) -> dict[str, int]:
        """Get the motor name dictionary assigning names to the motor numbers."""
        return self.call_action("get_motor_dict")

    def set_motor_dict(self, motor_dict: dict[str, int]) -> None:
        """Set a motor name dictionary assigning names to the motor numbers."""
        return self.call_action("set_motor_dict", motor_dict)

    # In/outs
    def get_analog_input(self, connection: int) -> float:
        """Return the analog input value of input `connection`."""
        return self.call_action("get_analog_input", connection)

    def get_digital_input(self, connection: int) -> bool:
        """Return the digital input value of input `connection`."""
        return self.call_action("get_digital_input", connection)

    def get_digital_output(self, connection: int) -> bool:
        """Return the state of the digital output with number `connection`."""
        return self.call_action("get_digital_output", connection)

    def set_digital_output(self, connection: int, enabled: bool) -> None:
        """Set the digital output at `connection` to bool `enabled`."""
        return self.call_action("set_digital_output", connection, enabled)
