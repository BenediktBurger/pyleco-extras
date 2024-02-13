# -*- coding: utf-8 -*-
"""
Testing motors

Created on Fri Jan 21 10:30:02 2022

@author: moneke
"""

import pytest

import pint

from pyleco_extras.actors.tmc import motor_utils


@pytest.fixture()
def config():
    return {'stepResolution': 3,
            'stepCount': 200,
            'unitSize': 1,
            'unitOffset': 0,
            'unitSymbol': "mm",
            }


class Test_stepsToUnits:
    values = ((0, 0),
              (100, 0.0625),
              (-21415, -13.384375),
              (124123234, 77577.02125),
              )

    @pytest.mark.parametrize("steps, units", values)
    def test_config(self, config, steps, units):
        assert motor_utils.stepsToUnits(steps, config) == units

    def test_offset(self, config):
        config['unitOffset'] = 5
        assert motor_utils.stepsToUnits(0, config) == 5


class Test_unitsToSteps:
    values = ((0, 0),
              (100, 0.0625),
              (-21415, -13.384375),
              (124123234, 77577.02125),
              (100, "62.5 um"),
              (124123234, "77.57702125 m"),
              (124123234, "77577.02125"),
              )

    @pytest.mark.parametrize("steps, units", values)
    def test_config(self, config, steps, units):
        assert motor_utils.unitsToSteps(units, config) == steps

    def test_offset(self, config):
        config['unitOffset'] = 5
        assert motor_utils.unitsToSteps(5, config) == 0

    def test_wrong_units(self, config):
        with pytest.raises(pint.DimensionalityError):
            motor_utils.unitsToSteps("5 kg", config)


class Test_toSignedInt:
    values = ((0, 0),
              (1, 1),
              (2, 2),
              (126, 126),
              (127, 127),
              (128, -128),
              (129, -127),
              (130, -126),
              (254, -2),
              (255, -1),
              )

    @pytest.mark.parametrize("unsigned, signed", values)
    def test_conversion(self, unsigned, signed):
        assert motor_utils.toSignedInt(unsigned, 8) == signed

    def test_32bit(self):
        assert motor_utils.toSignedInt(-12345+2**32) == -12345
