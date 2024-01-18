"""
GUI to control the starter

created on 23.11.2020 by Benedikt Moneke
"""

# Standard packages.
from enum import Enum
import logging
from typing import Dict, Tuple

# 3rd party packages.
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QColor

from pyleco.directors.starter_director import StarterDirector
from pyleco.core.message import Message
from pyleco.management.starter import Status

from devices.base_main_window import LECOBaseMainWindow
from devices.gui_utils import start_app

# Local packages.
from data.Settings import Settings

logging.getLogger("PyQt6").setLevel(logging.INFO)
log = logging.getLogger(__name__)
gLog = logging.getLogger()
h = logging.StreamHandler()
gLog.addHandler(h)


class StarterColors(Enum):
    """Colors for the starters themselves."""
    CONNECTED = QColor("DarkGreen")
    DISCONNECTED = QColor("DarkRed")


class TaskColors(Enum):
    """Colors of the tasks."""
    STARTING = QColor("SkyBlue")  # Told to start
    RUNNING = QColor("Lime")  # Currently running
    STALLED = QColor("red")  # Started but not running anymore
    STOPPING = QColor("yellow")  # Told to stop
    STOPPED = QColor("LightGray")  # Gracefully stopped


def status_to_color(status):
    """Return the color for a given status."""
    if status & Status.RUNNING:
        return TaskColors.RUNNING.value
    elif status & Status.INSTALLED:
        return TaskColors.STARTING.value
    elif status & Status.STARTED:
        return TaskColors.STALLED.value
    elif status == -1:
        # TODO for deprecation reasons
        return TaskColors.STALLED.value
    else:
        # Neither running, nor should it run.
        return TaskColors.STOPPED.value


class StarterItem(QtGui.QStandardItem):
    pass


class StarterGUI(LECOBaseMainWindow):
    """Control starter programs."""

    tv: QtWidgets.QTreeView

    def __init__(self, name="StarterGUI", host="localhost", **kwargs):
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, host=host, ui_file_name="StarterGUI", logger=gLog,
                         settings_dialog_class=Settings,
                         **kwargs)

        # Get settings.
        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(QtCore.QByteArray(geometry))
        self.setSettings()

        self.cids: Dict[bytes, Tuple[str, StarterItem]] = {}  # key: conversation id
        self.director = StarterDirector(communicator=self.communicator)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.request_task_states)

        self.create_model()

        # Connect actions to slots.
        self.actionAdd.triggered.connect(self.add_starter)
        self.actionReload.triggered.connect(self.reload_pressed)
        self.actionStopStarter.triggered.connect(self.stop_starter)
        self.actionRemove.triggered.connect(self.remove_starter)

        self.actionStart.triggered.connect(self.start_action)
        self.actionStop.triggered.connect(self.stop_action)
        self.actionRestart.triggered.connect(self.restart_action)
        self.actionInstall.triggered.connect(self.install_action)

        log.info("Starter initialized.")
        self.timer.start(1000)

    @pyqtSlot()
    def closeEvent(self, event):
        """Clean up if the window is closed somehow."""
        log.info("Closing.")
        self.stop_listen()

        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        starters = []
        for i in range(self.model_root.rowCount()):
            starters.append(self.model_root.child(i).data(Qt.ItemDataRole.DisplayRole))
        settings.setValue("starters", starters)
        # accept the close event (reject it, if you want to do something else)
        event.accept()

    @pyqtSlot(Message)
    def message_received(self, message: Message) -> None:
        """Handle a message received via the Communicator."""
        action = self.cids.get(message.conversation_id, None)
        log.debug(f"Message from {message.sender} with {message.conversation_id} and "
                  f"{message.data} received. Action: {action}")
        if not action:
            log.warning(f"Could not interpret {message.data} from {message.sender}.")
            return
        match action:  # noqa
            case "status_tasks", starter:
                self.set_starter_status(starter, message.data)  # type: ignore
            case "list_tasks", starter:
                self.create_task_list(starter, message.data)  # type: ignore

    def create_model(self):
        """Create the model."""
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Starters"])
        self.model_root = self.model.invisibleRootItem()
        self.tv.setModel(self.model)
        self.sm = self.tv.selectionModel()

        # Add the starters from the last usage
        settings = QtCore.QSettings()
        for name in settings.value("starters", type=list):
            starter = self.add_starter()
            starter.setData(name, Qt.ItemDataRole.EditRole)
            self.request_task_list(starter)

    def add_starter(self):
        """Add an unnamed starter."""
        starter = StarterItem("Unnamed Starter")
        self.model_root.appendRow(starter)
        return starter

    def remove_starter(self):
        """Remove the selected starter(s)."""
        indices = self.sm.selectedIndexes()
        for index in indices:
            item = self.model.itemFromIndex(index)
            if isinstance(item, StarterItem):
                self.model_root.removeRow(index.row())

    @pyqtSlot()
    def reload_pressed(self):
        """Reload tasks for the selected starter(s)."""
        indices = self.sm.selectedIndexes()
        for index in indices:
            item = self.model.itemFromIndex(index)
            if isinstance(item, StarterItem):
                self.request_task_list(item)

    def request_task_list(self, starter: StarterItem) -> None:
        name = starter.data(Qt.ItemDataRole.DisplayRole)
        cid = self.director.ask_rpc_async(method="list_tasks", actor=name)
        self.cids[cid] = ("list_tasks", starter)

    def create_task_list(self, starter: StarterItem, data: dict) -> None:
        try:
            tasks = data["result"]
        except (TypeError, KeyError):
            log.error(f"Reading tasks failed with {data}.")
        else:
            starter.removeRows(0, starter.rowCount())
            for task in tasks:
                item = QtGui.QStandardItem(task['name'])
                item.setToolTip(task.get('tooltip'))
                item.setEditable(False)
                starter.appendRow(item)
            index = self.model.indexFromItem(starter)
            self.tv.setExpanded(index, True)

    @pyqtSlot()
    def request_task_states(self):
        """Request the states of the tasks."""
        for i in range(self.model_root.rowCount()):
            # Do all starters
            starter = self.model_root.child(i)
            name = starter.data(Qt.ItemDataRole.DisplayRole)
            cid = self.director.ask_rpc_async(method="status_tasks", actor=name)
            self.cids[cid] = ("status_tasks", starter)  # type: ignore

    def set_starter_status(self, starter: StarterItem, data: dict) -> None:
        """Set the status of `starter`'s tasks."""
        try:
            status = data["result"]
        except (TypeError, KeyError):
            log.error(f"Reading '{starter}' status failed with '{data}'.")
            # TODO do propererror handling
            # if content and content[0] == Errors.RECEIVER_UNKNOWN:
            starter.setBackground(StarterColors.DISCONNECTED.value)
        else:
            starter.setBackground(StarterColors.CONNECTED.value)
            for j in range(starter.rowCount()):
                # Do all tasks
                task = starter.child(j)
                try:
                    s = status.pop(task.data(Qt.ItemDataRole.DisplayRole))
                except KeyError:
                    s = Status.STOPPED
                task.setBackground(status_to_color(s))
            for name, s in status.items():
                # Add running, but not yet known, tasks to the task list
                item = QtGui.QStandardItem(name)
                item.setEditable(False)
                item.setBackground(status_to_color(s))
                starter.appendRow(item)

    def filter_selected_tasks(self, color=None):
        """Read all the tasks from the selection and return a dict of starters and tasks.

        :param color: Set the task to this color, if specified.
        :return: Dictionary of starter names and the objects.
        :return: Dictionary of the starter name and selected tasks of that starter.
        """
        starters = {}
        tasks = {}
        indices = self.sm.selectedIndexes()
        for index in indices:
            item = self.model.itemFromIndex(index)
            if isinstance(item, StarterItem):
                continue
            starter = item.parent()
            starter_name = starter.data(Qt.ItemDataRole.DisplayRole)
            if starter_name not in starters.keys():
                starters[starter_name] = starter
                tasks[starter_name] = []
            tasks[starter_name].append(item.data(Qt.ItemDataRole.DisplayRole))
            if color is not None:
                item.setBackground(color)
        return starters, tasks

    def start_action(self):
        starters, tasks = self.filter_selected_tasks(TaskColors.STARTING.value)
        for name, starter in starters.items():
            try:
                self.director.start_tasks(tasks[name], actor=name)
            except (AttributeError, TimeoutError, ConnectionError):
                pass  # going to be handled later

    def stop_action(self):
        starters, tasks = self.filter_selected_tasks(TaskColors.STOPPING.value)
        for name, starter in starters.items():
            try:
                self.director.stop_tasks(tasks[name], actor=name)
            except (AttributeError, TimeoutError, ConnectionError):
                pass  # going to be handled later

    def restart_action(self):
        starters, tasks = self.filter_selected_tasks(TaskColors.STARTING.value)
        for name, starter in starters.items():
            try:
                self.director.restart_tasks(tasks[name], actor=name)
            except (AttributeError, TimeoutError, ConnectionError):
                pass  # going to be handled later

    def install_action(self):
        starters, tasks = self.filter_selected_tasks()
        for name, starter in starters.items():
            try:
                self.director.install_tasks(tasks[name], actor=name)
            except (AttributeError, TimeoutError, ConnectionError):
                pass  # going to be handled later

    def stop_starter(self):
        indices = self.sm.selectedIndexes()
        for index in indices:
            item = self.model.itemFromIndex(index)
            if isinstance(item, StarterItem):
                name = item.data(Qt.ItemDataRole.DisplayRole)
                try:
                    self.director.shut_down_actor(actor=name)
                except (AttributeError, TimeoutError, ConnectionError):
                    pass


if __name__ == '__main__':  # if this is the started script file
    """Start the main window if this is the called script file."""
    start_app(main_window_class=StarterGUI, logger=gLog)
