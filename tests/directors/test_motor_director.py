
from inspect import getfullargspec

import pytest

from pyleco.test import FakeDirector

from pyleco_extras.directors.tmc_motor_director import TMCMotorDirector
from pyleco_extras.actors.tmc_motor_actor import TMCMotorActor


class FakeMotorDirector(FakeDirector, TMCMotorDirector):
    pass


@pytest.fixture
def motor_director():
    return FakeMotorDirector(actor="remote", remote_class=TMCMotorActor)


general_methods: list[str] = [
    "disconnect",
    "configure_motor",
    "get_global_parameter",
    "set_global_parameter",
    "get_axis_parameter",
    "set_axis_parameter",
    "get_motor_dict",
    "set_motor_dict",
]

motor_read_methods = [
    "get_configuration",
    "stop",
    "get_actual_velocity",
    "get_actual_position",
    "get_actual_units",
    "get_position_reached",
    "get_analog_input",
    "get_digital_input",
    "get_digital_output",
]

motor_write_methods = [
    "set_actual_position",
    "move_to",
    "move_to_units",
    "move_by",
    "move_by_units",
    "rotate",
]

io_read_methods = [
    "get_analog_input",
    "get_digital_input",
    "get_digital_output",
]

io_write_methods = [
    "set_digital_output"
]


@pytest.mark.parametrize(
        "method",
        general_methods + motor_read_methods + motor_write_methods + io_read_methods
        + io_write_methods
        )
def test_start_collecting_signature(method: str):
    orig_spec = getfullargspec(getattr(TMCMotorActor, method))
    dir_spec = getfullargspec(getattr(TMCMotorDirector, method))
    assert orig_spec == dir_spec


@pytest.mark.parametrize("method", motor_write_methods)
def test_method_call_existing_remote_motor_write_methods(motor_director: FakeMotorDirector,
                                                         method: str):
    motor_director.return_value = 5
    assert getattr(motor_director, method)(1, 2) == 5
    # asserts that no error is raised in the "ask_rpc" method


@pytest.mark.parametrize("method", motor_read_methods)
def test_method_call_existing_remote_motor_read_methods(motor_director: FakeMotorDirector,
                                                        method: str):
    motor_director.return_value = 5
    assert getattr(motor_director, method)(1) == 5
    # asserts that no error is raised in the "ask_rpc" method


@pytest.mark.parametrize("method", io_write_methods)
def test_method_call_existing_remote_io_write_methods(motor_director: FakeMotorDirector,
                                                      method: str):
    motor_director.return_value = 5
    assert getattr(motor_director, method)(1, 2) == 5
    # asserts that no error is raised in the "ask_rpc" method


@pytest.mark.parametrize("method", io_read_methods)
def test_method_call_existing_remote_io_read_methods(motor_director: FakeMotorDirector,
                                                     method: str):
    motor_director.return_value = 5
    assert getattr(motor_director, method)(1) == 5
    # asserts that no error is raised in the "ask_rpc" method
