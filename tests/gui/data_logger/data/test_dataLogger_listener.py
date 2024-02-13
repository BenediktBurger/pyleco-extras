
import pytest
from pyleco.test import FakeContext

from pyleco_extras.gui.data_logger.data.data_logger_listener import DataLoggerCore, Signals


@pytest.fixture
def signals() -> Signals:
    return Signals()


@pytest.fixture
def data_logger(signals: Signals) -> DataLoggerCore:
    return DataLoggerCore(name="listener", signals=signals, context=FakeContext())


def test_make_datapoint(data_logger: DataLoggerCore, qtbot):
    datapoint = {'time': 150}

    def calculate_data():
        return datapoint

    data_logger.calculate_data = calculate_data
    with qtbot.waitSignal(data_logger.signals.datapoint_ready, timeout=0) as blocker:
        assert data_logger.make_datapoint() == datapoint  # should return datapoint
    assert blocker.args == [datapoint]  # should emit datapoint


def test_set_configuration(data_logger: DataLoggerCore, qtbot):
    data = {"some": 5}
    with qtbot.waitSignal(data_logger.signals.configuration_changed) as blocker:
        data_logger.set_configuration(data)
    assert blocker.args == [data]


def test_set_plot_configuration(data_logger: DataLoggerCore, qtbot):
    data = [{"some": 5}]
    with qtbot.waitSignal(data_logger.signals.plot_configuration_changed) as blocker:
        data_logger.set_plot_configuration(data)
    assert blocker.args == [data]
