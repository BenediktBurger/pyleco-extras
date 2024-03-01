"""
Data logger in order to log data and do automatic measurements

classes
-------
DataLogger
    The main program, called if this module is executed.

Created on Thu Apr  1 15:14:39 2021 by Benedikt Burger
"""

# Standard packages.
import logging
from typing import Any, Optional

# 3rd party

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSlot

from pyleco.management.data_logger import TriggerTypes
from pyleco.utils.pipe_handler import CommunicatorPipe

from pyleco_extras.gui_utils import base_main_window
from pyleco_extras.gui_utils.base_main_window import start_app
from pyleco_extras.gui.data_logger.data_logger_base import DataLoggerBase
from pyleco_extras.gui.data_logger.data.settings import Settings
from pyleco_extras.gui.data_logger.data.data_logger_listener import DataLoggerListener
try:
    from pyleco.json_utils.errors import ServerError
except ModuleNotFoundError:
    from jsonrpcobjects.errors import ServerError


nan = float("nan")

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())


# replace the QtListener with our own Listener
base_main_window.QtListener = DataLoggerListener


class DataLoggerGUI(DataLoggerBase):
    """Log and show data.

    The data logger listens to commands via the control protocol and to data via the data protocol.
    Whenever triggered, either by a timer or by receiving certain data via data protocol, it
    generates a data point.
    Each new datapoint is published via the data protocol, such that a user might follow the data
    acquisition.
    The data point contains values for each variable. The value is either the last one received
    since the last data point, or the average of all values received sind the last data point, or
    `float("nan")`.

    Commands via control protocol can control the data logger or request the last data point.

    :param name: Name of this program.
    :param host: Host of the Coordinator.
    """

    listener: DataLoggerListener
    communicator: CommunicatorPipe

    def __init__(self, name: str = "DataLogger", host: str = "localhost", **kwargs) -> None:
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, settings_dialog_class=Settings, host=host, **kwargs)

        # Setup of Listener.
        self.listener.signals.started.connect(self.setup_started)
        self.listener.signals.configuration_changed.connect(self.set_configuration)
        self.listener.signals.datapoint_ready.connect(self.show_data_point)
        self.listener.signals.plot_configuration_changed.connect(self.set_plot_configuration)

        # Start a measurement according to last values.
        self.user_data = None
        self.start()
        self.tabWidget.setCurrentIndex(0)

    def setup_actions(self) -> None:
        super().setup_actions()
        self.actionStart.triggered.connect(self.start)
        self.actionSave.triggered.connect(self.saveDataClicked)
        self.actionPause.toggled.connect(self.pause)
        self.actionCopyLastDatapoint.triggered.connect(self.copy_last_data_point)

    def setup_buttons(self) -> None:
        super().setup_buttons()
        # Trigger
        self.cbTimer.toggled.connect(self.toggleTimer)
        self.sbTimeout.valueChanged.connect(self.setTimerInterval)
        self.leTrigger.editingFinished.connect(self.setTriggerVariable)

    def setup_timers(self):
        super().setup_timers()
        # For auto save feature
        self.auto_save_timer = QtCore.QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(1000000000)  # just a number, will be changed in setSettings

    @property
    def lists(self) -> dict[str, list[Any]]:
        # for the plots
        return self.listener.message_handler.lists

    @lists.setter
    def lists(self, value) -> None:
        pass  # don't do anything

    # Control Application
    def setSettings(self):
        """Apply settings."""
        super().setSettings()
        settings = QtCore.QSettings()
        # 1 min = 60 * 1000 * 1 ms
        self.auto_save_timer.setInterval(settings.value("autoSaveInterval", 60, int) * 60 * 1000)

    # Data management
    def save_data(self, meta: Optional[dict] = None, suffix: str = "") -> str:
        """Save the data.

        :param dict meta: The meta data to save. Use e.g. in subclass
            Protected keys: units, today, name, configuration, user.
        :param str suffix: Suffix to append to the filename.
        """
        # Preparation.
        self.leSavedName.setText("Saving...")
        self.statusBar().showMessage("Saving...")
        settings = QtCore.QSettings()
        folder = settings.value("savePath", type=str)
        self.listener.message_handler.directory = folder
        if meta is None:
            meta = {}

        try:
            file_name = self.communicator.ask_handler(
                method="save_data",
                timeout=30,
                header=f"{self.leHeader.toPlainText()}\n{self.leVariables.text()}",
                meta=meta,
                suffix=suffix,
            )
        except Exception as exc:
            log.exception("Some type error during saving occurred.", exc_info=exc)
            self.leSavedName.setText("Error")
            self.statusBar().showMessage(f"Writing failed due to Error. {exc}", 5000)
            raise
        else:
            # Indicate the name.
            log.info(f"Saved data to '{folder}/{file_name}'.")
            self.leSavedName.setText(file_name)
            self.statusBar().showMessage(f"Saved data to '{folder}/{file_name}'.", 5000)
            return file_name

    @pyqtSlot()
    def auto_save(self):
        """Make a automatic save, if action is checked."""
        if self.actionAutoSave.isChecked():
            self.save_data(suffix="_auto")

    # GUI control
    @pyqtSlot()
    def start(self) -> None:
        """Start a measurement."""
        try:
            self.communicator.ask_handler(
                method="start_collecting",
                variables=self.variables,
                units=self.units,
                trigger_type=self.trigger_type,
                trigger_timeout=self.trigger_timeout,
                trigger_variable=self.trigger_variable,
                valuing_mode=self.valuing_mode,
                value_repeating=self.value_repeating,
            )
        except ServerError as exc:
            self.statusBar().showMessage(f"Communication error: {exc.rpc_error.message}", 3000)
        except (ConnectionError, TimeoutError) as exc:
            log.exception("set property communication error", exc_info=exc)

    def setup_started(self):
        self.current_units = self.units

        # Clear the interface.
        self.statusBar().clearMessage()
        self.lbCount.setText("Data points: 0")
        self.signals.started.emit()
        self.tabWidget.setCurrentIndex(1)
        self.actionPause.setChecked(False)  # TODO previous?

    @pyqtSlot(bool)
    def toggleTimer(self, checked: bool) -> None:
        """Start or stop the timer."""
        if checked:
            self.setTimerInterval(self.sbTimeout.value())
            self.communicator.ask_handler("set_trigger_type", trigger_type=TriggerTypes.TIMER)
        else:
            self.setTriggerVariable()
            self.communicator.ask_handler("set_trigger_type", trigger_type=TriggerTypes.VARIABLE)

    @pyqtSlot(int)
    def setTimerInterval(self, value: int) -> None:
        """Set the timer interval to `value` ms."""
        self.communicator.ask_handler("set_trigger_interval", interval=value / 1000)

    @pyqtSlot()
    def setTriggerVariable(self) -> None:
        variable = self.leTrigger.text()
        self.communicator.ask_handler("set_trigger_variable", variable=variable)

    @pyqtSlot(bool)
    def pause(self, checked: bool):
        """Pause a measurement."""
        self.communicator.ask_handler(method="pause", pause_enabled=checked)

    @pyqtSlot()
    def saveDataClicked(self):
        """Save the data and store the filename in the clipboard."""
        try:
            name = self.save_data()
        except (PermissionError, TypeError):
            pass  # Log is already written
        else:
            clipboard = QtWidgets.QApplication.instance().clipboard()  # type: ignore
            clipboard.setText(name)


if __name__ == "__main__":  # pragma: no cover
    start_app(DataLoggerGUI)
