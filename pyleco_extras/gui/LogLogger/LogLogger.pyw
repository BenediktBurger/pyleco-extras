"""
Main file of the LogLogger.

This program logs log entries of other programs

created on 22.2.2023 by Benedikt Burger
"""

# Standard packages.
import logging
from logging.handlers import QueueHandler
from typing import Any, Optional

# 3rd party packages.
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot, Qt

from pyleco.utils.zmq_log_handler import ZmqLogHandler
from pyleco.utils.log_levels import get_leco_log_level
from pyleco.core import LOG_SENDING_PORT
from pyleco.core.data_message import DataMessage, MessageTypes

from pyleco_extras.gui_utils.base_main_window import LECOBaseMainWindowDesigner, start_app
from pyleco_extras.gui.LogLogger.data.settings import Settings


log = logging.getLogger(__name__)
gLog = logging.getLogger()
gLog.addHandler(logging.StreamHandler())

logging.getLogger("PyQt6").setLevel(logging.INFO)


class Item(QtGui.QStandardItem):
    pass


class SignalHandler(QueueHandler):
    """Handle logs emitting a Qt signal."""

    def __init__(self, **kwargs) -> None:
        self.signals = self.Signals()
        super().__init__(self.signals.log, **kwargs)  # type: ignore

    class Signals(QtCore.QObject):
        log = QtCore.pyqtSignal(str, list)

    def enqueue(self, record: Any) -> None:
        """Enqueue a message, if the fullname is given."""
        self.queue.emit('self', record)  # type: ignore

    prepare = ZmqLogHandler.prepare  # type: ignore


class LogLogger(LECOBaseMainWindowDesigner):
    """Log log entries emitted from other software."""

    leSender: QtWidgets.QLineEdit
    pbSubscribe: QtWidgets.QPushButton
    bbSender: QtWidgets.QComboBox

    tableView: QtWidgets.QTableView
    splitter: QtWidgets.QSplitter
    leDetails: QtWidgets.QPlainTextEdit

    def __init__(self, name: str = "LogLogger", host: str = "localhost", **kwargs) -> None:
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, ui_file_name="LogLogger",
                         settings_dialog_class=Settings,
                         host=host, data_port=LOG_SENDING_PORT,
                         **kwargs)

        self.restoreConfiguration()

        self.models: dict[str, QtGui.QStandardItemModel] = {'self': self.createModel()}
        self.bbSender.addItems(["self"])
        self.setModel("self")
        self.subscription: list[str] = []

        shandler = SignalHandler()
        shandler.signals.log.connect(self.add_log_entry)
        gLog.addHandler(shandler)

        self.listener.signals.dataReady.connect(self.add_entry_old_style)
        self.listener.signals.data_message.connect(self.add_entry_from_message)
        self.setSettings()

        self.sm: QtCore.QItemSelectionModel = self.tableView.selectionModel()
        self.sm.currentChanged.connect(self.showItemDetails)

        # Connect actions to slots.
        self.actionSave.triggered.connect(self.save)
        self.actionReset.triggered.connect(self.reset)
        self.actionSet_Debug.triggered.connect(self.set_debug)
        self.actionSet_Info.triggered.connect(self.set_info)
        self.actionSet_Warning.triggered.connect(self.set_warning)
        self.actionSet_Error.triggered.connect(self.set_error)
        self.actionRescale.triggered.connect(self.rescale_log)

        # Connect widgets
        self.bbSender.currentTextChanged.connect(self.setModel)
        self.pbSubscribe.clicked.connect(self.subscribe)

        self.subscribe()
        log.info("LogLogger initialized.")

    @staticmethod
    def createModel() -> QtGui.QStandardItemModel:
        """Create a new Model."""
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels(["Time", "Severity", "Logger", "Message"])
        return model

    def restoreConfiguration(self) -> None:
        """Restore configuration from the last time."""
        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(QtCore.QByteArray(geometry))
        splitterState = settings.value("splitter")
        if splitterState is not None:
            self.splitter.restoreState(splitterState)
        self.leSender.setText(settings.value("names", type=str))
        self.lastNode = settings.value("lastNode", type=str)

    @pyqtSlot()
    def closeEvent(self, event) -> None:
        """Clean up if the window is closed somehow."""
        log.info("Closing.")
        self.stop_listen()
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("splitter", self.splitter.saveState())
        settings.setValue("names", self.leSender.text())
        settings.setValue("lastNode", self.communicator.namespace)

        # accept the close event (reject it, if you want to do something else)
        event.accept()

    # Workings
    def generate_full_name(self, name: str) -> str:
        """Generate a full name of `name`."""
        if "." in name:
            return name
        else:
            try:
                fname = ".".join((self.communicator.namespace, name))
            except TypeError:
                fname = ".".join((self.lastNode, name))
            return fname

    def subscribe(self) -> None:
        """Unsubscribe to old values and subscribe to new ones.

        If the Node is not given, the local node is assumed.
        """
        old_keys = self.subscription
        new_keys: list[str] = self.leSender.text().split()
        for key in old_keys:
            if key not in new_keys:
                name = self.generate_full_name(key)
                self.communicator.unsubscribe(name)
                try:
                    if not self.models[name].rowCount():
                        del self.models[name]
                        index = self.bbSender.findText(name)
                        self.bbSender.removeItem(index)
                except KeyError:
                    pass
        for key in new_keys:
            name = self.generate_full_name(key)
            if name not in old_keys:
                self.communicator.subscribe(name)
            if name not in self.models:
                self.models[name] = self.createModel()
                self.bbSender.addItem(name)
        self.subscription = new_keys  # text of subscribed Loggers.

    @pyqtSlot(DataMessage)
    def add_entry_from_message(self, message: DataMessage) -> None:
        self.add_log_entry(emitter=message.topic.decode(), log_entry=message.data)

    @pyqtSlot(dict)
    def add_entry_old_style(self, data: dict[str, list[str]]) -> None:
        """Add a log entry."""
        for key, value in data.items():
            self.add_log_entry(emitter=key, log_entry=value)

    def add_log_entry(self, emitter: str, log_entry: list[str]) -> None:
        """Add a log entry."""
        scrollbar = self.tableView.verticalScrollBar()
        follow = scrollbar.value() == scrollbar.maximum()
        try:
            self.models[emitter].appendRow([Item(v) for v in log_entry])
        except KeyError:
            self.models[emitter] = self.createModel()
            self.models[emitter].appendRow([Item(v) for v in log_entry])
            self.bbSender.addItem(emitter)
        except Exception as exc:
            log.exception("Adding entry failed.", exc_info=exc)
        if follow:
            self.tableView.scrollToBottom()

    @pyqtSlot(str)
    def setModel(self, name: str) -> None:
        """Choose a model to display."""
        self.current_name: str = name
        self.current: QtGui.QStandardItemModel = self.models[name]
        self.tableView.setModel(self.current)
        self.rescale_log()
        sm: QtCore.QItemSelectionModel = self.tableView.selectionModel()
        sm.currentChanged.connect(self.showItemDetails)

    def showItemDetails(self, current: QtCore.QModelIndex,
                        previous: Optional[QtCore.QModelIndex] = None) -> None:
        """Show the details of that item."""
        self.leDetails.setPlainText(
            self.current.itemFromIndex(current).data(Qt.ItemDataRole.DisplayRole))

    @pyqtSlot()
    def save(self) -> None:
        """Save the current log into a file."""
        settings = QtCore.QSettings()
        folder = settings.value('savePath', type=str)
        with open(f"{folder}/{self.bbSender.currentText()}.txt", "a") as file:
            file.writelines(
                ["\t".join(
                    [self.current.item(row, column).data(
                        Qt.ItemDataRole.DisplayRole) for column in range(
                            self.current.columnCount())]
                ) + "\n" for row in range(self.current.rowCount())])

    @pyqtSlot()
    def reset(self) -> None:
        """Reset a model."""
        self.current.clear()
        self.current.setHorizontalHeaderLabels(["Time", "Severity", "Logger", "Message"])

    @pyqtSlot()
    def set_debug(self) -> None:
        """Set logging level to DEBUG."""
        self.set_logging_level(logging.DEBUG)

    @pyqtSlot()
    def set_info(self) -> None:
        """Set logging level to INFO."""
        self.set_logging_level(logging.INFO)

    @pyqtSlot()
    def set_warning(self) -> None:
        """Set logging level to WARNING."""
        self.set_logging_level(logging.WARNING)

    @pyqtSlot()
    def set_error(self) -> None:
        """Set logging level to ERROR."""
        self.set_logging_level(logging.ERROR)

    def set_logging_level(self, level: int) -> None:
        """Set the logging level."""
        if self.current_name == "self":
            gLog.setLevel(level)
        else:
            level = get_leco_log_level(level).value
            self.communicator.send(receiver=self.current_name, data={
                'id': 1, 'method': "set_log_level",
                "params": {"level": level}, "jsonrpc": "2.0"},
                message_type=MessageTypes.JSON,
                )

    @pyqtSlot()
    def rescale_log(self) -> None:
        """Rescale the log table to the content."""
        self.tableView.resizeColumnsToContents()
        self.tableView.resizeRowsToContents()
        self.tableView.horizontalHeader().setStretchLastSection(True)

    # TODO
    # add sorting, see https://doc.qt.io/qt-6/qtwidgets-itemviews-customsortfiltermodel-example.html


if __name__ == '__main__':  # if this is the started script file
    """Start the main window if this is the called script file."""
    start_app(main_window_class=LogLogger)
