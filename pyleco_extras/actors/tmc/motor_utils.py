# -*- coding: utf-8 -*-
"""
Often used code for configuration and usage of stepper motors.

classes
-------
MotorSettings
    Settings dialog to configuring a TMC motor.

methods
-------
configureMotor
    Configure a motor according to the configuration dictionary.
getPort
    Get the port of a specific card.
stepsToUnits
    Convert microsteps to units.
unitsToSteps
    Convert units to microsteps.
toSignedInt
    Convert an unsigned integer to a signed one, for example TMCL axis
    parameters.

motor configuration definition
------------------------------
motorNumber
    Number of the motor connector on the motor card. Starts at 0.
maxCurrent
    Maximum current in Percent of motor card current.
standbyCurrent
    Standby current in Percent of motor card current.
positioningSpeed
    Maximum velocity used for reaching a position in position mode.
acceleration
    Maximum acceleration used for reaching a desired velocity.
stepResolution
    Indicates the number of steps per fullstep. It is the exponent of 2.
    A stepResolution of 3 means 2**3=8 steps per fullstep.
stepCount
    Number of fullsteps per one motor revolution, typically 200.
unitSize
    Amount of units per one motor revolution, for example 360.
unitSymbol
    Symbol of the shown unit, for example °.
unitOffset
    Amount of units, if the motor is at 0 steps.
stallguardThreshold
    Sensitivity, when to stop the motor if it is blocked. Between -64 and +63


Created on 14.01.2022 by Benedikt Moneke
"""

from typing import Any

import pint
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Slot as pyqtSlot  # type: ignore

from pyleco_extras.gui_utils.base_settings import BaseSettings
from pyleco_extras.utils.units import ureg, assume_units


# Configuration dictionary for the normal motors.
default_config = {
    'motorNumber': 0,
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
}


class MotorSettings(BaseSettings):
    """Define the motor settings dialog and its methods."""

    def __init__(self, key: str, motorName: str = "Unknown motor", noMotor: bool = False,
                 **kwargs) -> None:
        """
        Initialize the dialog with the data for the motor `key`.

        Parameters
        ----------
        key : str
            Settings key under which to store the motor settings
        motorName : str
            Title of the window.
        noMotor : bool
            Whether for the whole card or a single motor.
        """
        self.key = key
        self.motor_name = motorName
        super().__init__(**kwargs)

        # Initialize
        self.onUnitSymbolChange()

    def setup_form(self, layout: QtWidgets.QFormLayout) -> None:
        layout.addRow(QtWidgets.QLabel(self.motor_name))
        motorNumber = QtWidgets.QSpinBox()
        motorNumber.setToolTip("Motor number of card.")
        self.add_value_widget("Motor", motorNumber, "motorNumber",
                              defaultValue=default_config["motorNumber"],
                              type=int)

        maxCurrent = QtWidgets.QSpinBox()
        maxCurrent.setSuffix(" %")
        maxCurrent.setRange(0, 100)
        maxCurrent.setToolTip("Maximum current relative to max module current.")
        self.add_value_widget("Max current", maxCurrent, "maxCurrent", default_config["maxCurrent"],
                              int)

        stbCurrent = QtWidgets.QSpinBox()
        stbCurrent.setSuffix(" %")
        stbCurrent.setRange(0, 100)
        stbCurrent.setToolTip("Current holding the motor relative to max module current.")
        self.add_value_widget("Standby current", stbCurrent, "standbyCurrent",
                              default_config["standbyCurrent"], int)

        positioningSpeed = QtWidgets.QSpinBox()
        positioningSpeed.setRange(1, 2047)
        positioningSpeed.setToolTip("Maximum speed for positioning.")
        self.add_value_widget("Positioning speed", positioningSpeed, "positioningSpeed",
                              default_config["positioningSpeed"], int)

        acceleration = QtWidgets.QSpinBox()
        acceleration.setRange(1, 2047)
        acceleration.setToolTip("Maximum acceleration during ramp-up/down.")
        self.add_value_widget("Max acceleration", acceleration, "acceleration",
                              default_config["acceleration"], int)

        step_resolution = QtWidgets.QComboBox()
        step_resolution.addItems(["fullstep", "halfstep", "4 microsteps", "8 microsteps",
                                  "16 microsteps", "32 microsteps", "64 microsteps",
                                  "128 microsteps", "256 microsteps"])
        step_resolution.setToolTip("Amount of steps per fullstep.")
        self.add_widget("Step resolution", widget=step_resolution,
                        setter=step_resolution.setCurrentIndex,
                        getter=step_resolution.currentIndex,
                        key="stepResolution",
                        defaultValue=default_config["stepResolution"],
                        type=int)

        steps_revolution = QtWidgets.QSpinBox()
        steps_revolution.setToolTip("Amount of full steps per motor revolution.")
        steps_revolution.setMaximum(2000)
        steps_revolution.setValue(200)
        self.add_value_widget("Steps/revolution", steps_revolution, "stepCount",
                              default_config["stepCount"], int)

        self.sbUnitSize = QtWidgets.QDoubleSpinBox()
        self.sbUnitSize.setToolTip("Amount of units per motor revolution.")
        self.sbUnitSize.setSuffix("°")
        self.sbUnitSize.setDecimals(9)
        self.sbUnitSize.setRange(-1000, 1000)
        self.sbUnitSize.setValue(360)
        self.add_value_widget("Unit/revolution", self.sbUnitSize, "unitSize",
                              default_config["unitSize"], float)

        self.sbUnitOffset = QtWidgets.QDoubleSpinBox()
        self.sbUnitOffset.setToolTip("Amount of units, if the motor is at 0 steps.")
        self.sbUnitOffset.setSuffix("°")
        self.sbUnitOffset.setDecimals(3)
        self.sbUnitOffset.setRange(-1000, 1000)
        self.add_value_widget("Unit offset", self.sbUnitOffset, "unitOffset",
                              default_config["unitOffset"], float)

        self.leUnitSymbol = QtWidgets.QLineEdit()
        self.leUnitSymbol.setToolTip("Symbol of measurement units.")
        self.leUnitSymbol.setText("°")
        self.add_widget("Unit symbol",
                        widget=self.leUnitSymbol,
                        getter=self.leUnitSymbol.text,
                        setter=self.leUnitSymbol.setText,
                        key="unitSymbol",
                        defaultValue=default_config["unitSymbol"],
                        type=str)
        self.leUnitSymbol.editingFinished.connect(self.onUnitSymbolChange)

        stall_guard_threshold = QtWidgets.QSpinBox()
        stall_guard_threshold.setToolTip("StallGuard sensitivity. The higher the less sensitive.")
        stall_guard_threshold.setRange(-64, 63)
        self.add_value_widget("Stall guard threshold", stall_guard_threshold, "stallguardThreshold",
                              default_config["stallguardThreshold"],
                              type=int)

    def readValues(self) -> None:
        """Read the stored values and show them on the user interface."""
        config: dict = self.settings.value(self.key, defaultValue={}, type=dict)
        for widget, name, value, typ in self.sets:
            widget.setValue(config.get(name, value))
        for getter, setter, name, value, typ in self.anyset:
            setter(config.get(name, value))

    @pyqtSlot()
    def restoreDefaults(self) -> None:
        super().restoreDefaults()
        self.onUnitSymbolChange()

    @pyqtSlot()
    def accept(self) -> None:
        """Save the values from the user interface in the settings."""
        config = {}
        for widget, name, value, typ in self.sets:
            config[name] = widget.value()
        for getter, setter, name, value, typ in self.anyset:
            config[name] = getter()
        self.settings.setValue(self.key, config)
        super().accept()  # make the normal accept things

    @pyqtSlot()
    def onUnitSymbolChange(self) -> None:
        """Adjust the unit suffix according to the symbol."""
        symbol = self.leUnitSymbol.text()
        self.sbUnitSize.setSuffix(symbol)
        self.sbUnitOffset.setSuffix(symbol)


def configureMotor(card, config: dict[str, Any]) -> None:
    """Configure a motor of `card` according to the dictionary `config`."""
    motor = card.motors[config['motorNumber']]
    motor.drive_settings.max_current = round(2.55 * config['maxCurrent'])
    motor.drive_settings.standby_current = round(2.55 * config['standbyCurrent'])
    motor.drive_settings.microstep_resolution = config['stepResolution']
    motor.linear_ramp.max_velocity = config['positioningSpeed']
    motor.linear_ramp.max_acceleration = config['acceleration']
    if 'stallguardThreshold' in config.keys():
        motor.stallguard2.threshold = config.get('stallguardThreshold')


def getPort(name: str) -> int:
    """Get the COM port number (int) of the card with `name`."""
    settings = QtCore.QSettings("NLOQO")
    address = settings.value(f"TMC/{name}", type=int)
    port = settings.value(f"TMCport/{address}", type=int)
    if port > 0:
        return port
    else:
        raise ValueError(f"No port found for {name}.")


def stepsToUnits(microsteps: int, config: dict) -> float:
    """Convert `microsteps` to a unit according to the motor `config`."""
    stepResolution = 2 ** config['stepResolution']  # microsteps per fullstep
    fStepsPerRev = config['stepCount']  # fullstep per revolution
    unitSize = config['unitSize']  # unit per revolution
    offset = config['unitOffset']  # offset in units
    return (microsteps / stepResolution / fStepsPerRev * unitSize) + offset


def stepsToUnitsQ(microsteps: int, config: dict) -> pint.Quantity:
    """Return a quantity from the `microsteps`."""
    return ureg.Quantity(stepsToUnits(microsteps, config),
                         config.get("unitSymbol", ""))  # type: ignore


def unitsToSteps(units: float | str | pint.Quantity, config: dict) -> int:
    """Convert `units` to microsteps according to motor `config`."""
    if isinstance(units, str):
        units = assume_units(units, config.get("unitSymbol", ""))
    if isinstance(units, pint.Quantity):
        units = units.m_as(config.get("unitSymbol", ""))  # type: ignore
    stepResolution = 2 ** config['stepResolution']  # microsteps per fullstep
    fStepsPerRev = config['stepCount']  # fullstep per revolution
    unitSize = config['unitSize']  # unit per revolution
    offset = config['unitOffset']  # offset in units
    return round((units - offset) / unitSize * fStepsPerRev * stepResolution)


def toSignedInt(unsigned: int, size: int = 32) -> int:
    """
    Convert an unsigned integer via "two's complement" to a signed one.

    The most significant bit indicates the sign. If it is set, the number is
    one less the negative of the other bits inverted.

    Parameters
    ----------
    unsigned
        The unsigned integer to convert.
    size
        Number of bits in the unsigned integer. Default is 32 for TMC.
    """
    if unsigned >= 1 << (size - 1):
        unsigned -= 1 << size
    return unsigned
