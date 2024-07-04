
import pytest

from pyleco_extras.gui.data_logger.data.plot_widget import DataLoggerGuiProtocol
from pyleco_extras.gui.data_logger.data_logger_base import DataLoggerBase


x_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
y_list = [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]


@pytest.fixture
def data_logger(qtbot) -> DataLoggerBase:
    dlg = DataLoggerBase(name="abc")
    dlg._lists = {
        "x": x_list,
        "y": y_list,
    }
    return dlg


def static_protocol_test():
    def verify_protocol(data_logger_gui: type[DataLoggerGuiProtocol]):
        pass
    verify_protocol(DataLoggerBase)


class Test_get_xy_data:
    def test_get_xy(self, data_logger: DataLoggerBase) -> None:
        result = data_logger.get_xy_data(x_key="x", y_key="y", start=1, stop=5)
        assert result == ([1, 2, 3, 4], [1, 4, 9, 16])

    def test_get_y(self, data_logger: DataLoggerBase):
        result = data_logger.get_xy_data(y_key="y")
        assert result == (y_list,)


def test_get_data_keys(data_logger: DataLoggerBase):
    assert list(data_logger.get_data_keys()) == ["x", "y"]


@pytest.mark.parametrize(
    "text, vars, units",
    (
        ("time:s, random", ["time", "random"], {"time": "s"}),
        (
            "time:s,\nSERVER.pub.var, .var2: W",
            ["time", "SERVER.pub.var", "SERVER.pub.var2"],
            {"time": "s", "SERVER.pub.var2": "W"},
        ),
        ("abc, .def", ["abc", ".def"], {}),
    ),
)
def test_interpret_variables_text(text, vars, units):
    assert DataLoggerBase._interpret_variables_and_units_text(text) == (vars, units)
