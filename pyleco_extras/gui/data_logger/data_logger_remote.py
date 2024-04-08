"""
Remotely control a DataLogger

Created on Thu Apr  1 15:14:39 2021 by Benedikt Burger
"""

# Standard packages.
import logging
from typing import Any

# 3rd party
import pint
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot

from pyleco.utils.qt_listener import DataMessage
from pyleco.management.data_logger import TriggerTypes
from pyleco.directors.data_logger_director import DataLoggerDirector

from pyleco_extras.gui_utils.base_main_window import start_app
from pyleco_extras.gui.data_logger.data_logger_base import DataLoggerBase
from pyleco_extras.gui.data_logger.data.settings_remote import Settings
try:
    from pyleco.json_utils.errors import ServerError
except ModuleNotFoundError:
    from jsonrpcobjects.errors import ServerError


log = logging.Logger(__name__)
log.addHandler(logging.StreamHandler())
u = pint.get_application_registry()
nan = float("nan")


class DataLoggerRemote(DataLoggerBase):
    """Remotely control a DataLogger.

    Control a DataLogger (be it the GUI or the non GUI version) remotely.
    Whenever the controlled DataLogger generates a new data point, this datapoint is added to the
    list and shown in the plots. ("follow" option)
    Alternatively, you can query in a regular interval for the last data point.

    :param name: Name of this program.
    :param host: Host of the Coordinator.
    """

    remote_length: int = 0

    def __init__(self, name: str = "DataLoggerRemote", host: str = "localhost", **kwargs) -> None:
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, settings_dialog_class=Settings, host=host, **kwargs)

        # Setup of Listener.
        self.listener.signals.dataReady.connect(self.dataReceived)
        self.listener.signals.data_message.connect(self.handle_data_message)

        self.lbRemoteCount = QtWidgets.QLabel()
        self.statusBar().addWidget(self.lbRemoteCount)  # type: ignore
        self.lbRemoteCount.show()
        self.actionReset = QtGui.QAction(
            "Reset local storage",
        )
        self.actionReset.setIconText("Reset")
        self.actionReset.setToolTip(
            "Reset the locally stored data points without touching the " "actual data acquisition."
        )
        self.actionReset.triggered.connect(self.reset)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionReset)

        self.current_units = self.units

        log.info(f"{name} initialized.")

    def setup_actions(self) -> None:
        super().setup_actions()
        self.actionStart.triggered.connect(self.start)
        self.actionSave.triggered.connect(self.saveDataClicked)
        self.actionPause.toggled.connect(self.pause)
        self.actionCopyLastDatapoint.triggered.connect(self.copy_last_data_point)

    def setup_buttons(self) -> None:
        super().setup_buttons()
        # Connect buttons to slots.
        # Trigger
        self.cbTimer.toggled.connect(self.toggleTimer)
        self.sbTimeout.valueChanged.connect(self.setTimerInterval)
        self.cbTrigger.toggled.connect(self.toggleVariable)
        self.leTrigger.textEdited.connect(self.setVariable)
        # Value
        self.cbValueLast.toggled.connect(self.toggleLast)
        self.cbValueMean.toggled.connect(self.toggleMean)
        self.cbRepeat.stateChanged.connect(self.toggleRepeat)
        # Text
        self.leHeader.textChanged.connect(self.set_header)
        self.leVariables.textEdited.connect(self.set_variables)

    def read_configuration(self) -> dict[str, Any]:
        try:
            config = self.communicator.ask_rpc(receiver=self.remote, method="get_configuration")
            length = self.communicator.ask_rpc(receiver=self.remote, method="get_list_length")
        except ServerError as exc:
            self.statusBar().showMessage(f"Communication error: {exc.rpc_error.message}", 10000)  # type: ignore
            return {}
        except Exception as exc:
            log.exception("Getting configuration failed.", exc_info=exc)
            return {}
        else:
            self.remote_length = length
            return config

    def reset(self):
        """Reset the local values to the remote one and reset the locally stored data points."""
        self.restore_configuration()
        self.current_units = self.units
        self.signals.started.emit()

    def set_properties(self, properties: dict[str, Any]) -> None:
        try:
            self.communicator.ask_rpc(
                receiver=self.remote, method="set_configuration", configuration=properties
            )
        except ServerError as exc:
            self.statusBar().showMessage(f"Communication error: {exc.rpc_error.message}", 3000)  # type: ignore
        except (ConnectionError, TimeoutError) as exc:
            log.exception("set property communication error", exc_info=exc)

    def set_property(self, name: str, value: Any) -> None:
        """Set a property remotely."""
        self.set_properties(properties={name: value})

    def setSettings(self):
        """Apply settings."""
        super().setSettings()
        settings = QtCore.QSettings()
        self.remote: str = settings.value("remoteName", "DataLogger", str)
        try:
            self.director.actor = self.remote
        except AttributeError:
            self.director = DataLoggerDirector(actor=self.remote, communicator=self.communicator)
        self.setWindowTitle(f"{self.communicator.name}: {self.remote}")
        self.communicator.unsubscribe_all()
        if settings.value("follow", True, bool):
            self.timer.stop()
            if "." in self.remote:
                remote = self.remote
            elif self.communicator.namespace is not None:
                remote = ".".join((self.communicator.namespace, self.remote))
            else:
                remote = self.remote
            log.debug(f"Subscribing '{remote}'.")
            self.communicator.subscribe(remote)
        else:
            self.timer.start(settings.value("interval", 1000, int))

    "GUI interaction"

    # Trigger
    @pyqtSlot(bool)
    def toggleNone(self, checked: bool) -> None:
        if checked:
            self.set_property("trigger_type", TriggerTypes.NONE)

    @pyqtSlot(bool)
    def toggleTimer(self, checked: bool) -> None:
        if checked:
            self.set_property("trigger_type", TriggerTypes.TIMER)

    @pyqtSlot(bool)
    def toggleVariable(self, checked: bool) -> None:
        if checked:
            self.set_property("trigger_type", TriggerTypes.VARIABLE)

    @pyqtSlot(int)
    def setTimerInterval(self, value: int) -> None:
        """Set the timer interval to `value`."""
        self.set_property("trigger_timeout", value / 1000)

    @pyqtSlot(str)
    def setVariable(self, value: str) -> None:
        self.set_property("trigger_variable", value)

    # Controls
    @pyqtSlot()
    def start(self):
        """Start a measurement."""
        self.director.start_collecting(
            variables=self.variables,  # type: ignore
            units=self.units,
            trigger_type=self.trigger_type,
            trigger_timeout=self.trigger_timeout,
            trigger_variable=self.trigger_variable,
            valuing_mode=self.valuing_mode,
            value_repeating=self.value_repeating,
        )
        self.reset()

    @pyqtSlot(bool)
    def pause(self, checked: bool):
        """Pause a measurement."""
        self.set_property("pause", checked)

    @pyqtSlot()
    def saveDataClicked(self):
        """Save the data and store the filename in the clipboard."""
        try:
            value = self.director.save_data()
        except ServerError as exc:
            self.statusBar().showMessage(f"Communication error: {exc.rpc_error.message}", 3000)  # type: ignore
        except Exception as exc:
            log.exception("saveDataClicked", exc_info=exc)
        else:
            self.savedName = value
            self.leSavedName.setText(value)
            clipboard = QtWidgets.QApplication.instance().clipboard()  # type: ignore
            clipboard.setText(self.savedName)

    # Value
    @pyqtSlot(bool)
    def toggleLast(self, checked: bool) -> None:
        if checked:
            self.set_property("value", "last")

    @pyqtSlot(bool)
    def toggleMean(self, checked: bool) -> None:
        if checked:
            self.set_property("value", "mean")

    @pyqtSlot(int)
    def toggleRepeat(self, state: int) -> None:
        self.set_property("valueRepeat", bool(state))

    # Text area
    @pyqtSlot()
    def set_header(self):
        text = self.leHeader.toPlainText()
        self.set_property("header", text)

    @pyqtSlot(str)
    def set_variables(self, text: str) -> None:
        self.set_property("variablesText", text)

    "Regular readout"

    def _add_datapoint_to_lists(self, datapoint: dict[str, Any]) -> None:
        for key, value in datapoint.items():
            if value is None:
                value = nan
            try:
                self.lists[key].append(value)
            except KeyError:
                self.lists[key] = [value]

    def _handle_new_data_point(self, datapoint: dict[str, Any], remote_length: int):
        self._add_datapoint_to_lists(datapoint=datapoint)
        self.show_data_point(datapoint)
        self.lbRemoteCount.setText(f"Remote data points: {remote_length}")

    @pyqtSlot()
    def make_data_point(self) -> None:
        """Store a datapoint."""
        try:
            length = self.communicator.ask_rpc(receiver=self.remote, method="get_list_length")
            datapoint = self.director.get_last_datapoint()
        except Exception as exc:
            log.exception("make_pata_point", exc_info=exc)
        else:
            if not isinstance(datapoint, dict):
                return
            self._handle_new_data_point(datapoint=datapoint, remote_length=length)

    # @pyqtSlot(dict)
    def dataReceived(self, data: dict[str, Any]) -> None:
        """Handle received data."""
        try:
            key, datapoint = data.popitem()
        except KeyError:
            return
        else:
            self.add_data_point(sender=key, datapoint=datapoint)

    def handle_data_message(self, message: DataMessage) -> None:
        data = message.data
        if isinstance(data, dict):
            self.add_data_point(sender=message.topic.decode(), datapoint=data)
        else:
            log.warning(f"Unknown data message {data} from {message.topic.decode()} received.")

    def add_data_point(self, sender: str, datapoint: dict[str, Any]) -> None:
        if sender.endswith(self.remote):
            self.remote_length += 1
            self._handle_new_data_point(datapoint=datapoint, remote_length=self.remote_length)
        else:
            log.warning(f"Unknown data message {datapoint} from {sender} received.")


if __name__ == "__main__":  # pragma: no cover
    start_app(DataLoggerRemote)
