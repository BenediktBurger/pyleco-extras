
import logging
from typing import Optional

from qtpy import QtCore, QtGui, QtWidgets, uic
from qtpy.QtCore import Slot  # type: ignore

from pyleco.core import COORDINATOR_PORT, PROXY_SENDING_PORT
from pyleco.core.internal_protocols import CommunicatorProtocol, SubscriberProtocol, Protocol
from pyleco.core.message import Message
from pyleco.utils.qt_listener import QtListener
from pyleco.utils.parser import parse_command_line_parameters
from pyleco.utils.data_publisher import DataPublisher


log = logging.getLogger("__main__")
log.addHandler(logging.NullHandler())


class FullCommunicator(CommunicatorProtocol, SubscriberProtocol, Protocol):
    pass


class _LECOBaseMainWindow(QtWidgets.QMainWindow):
    """Base MainWindow with the LECO protocol."""

    listener: QtListener
    communicator: FullCommunicator
    publisher: DataPublisher

    settings_dialog_class: type[QtWidgets.QDialog]
    actionClose: QtGui.QAction  # type: ignore
    actionSettings: QtGui.QAction  # type: ignore

    def __init__(self,
                 name: str,
                 settings_dialog_class: Optional[type[QtWidgets.QDialog]] = None,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: logging.Logger = log,
                 data_port: int = PROXY_SENDING_PORT,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        # Load the user interface file and show it.
        self._setup_ui()
        self.setWindowTitle(name)
        self.show()
        if settings_dialog_class is not None:
            self.settings_dialog_class = settings_dialog_class

        # Set the application name
        if (app := QtCore.QCoreApplication.instance()):
            app.setOrganizationName("NLOQO")
            app.setApplicationName(name)

        # create the listener and the communicator
        self.publisher = DataPublisher(full_name=name)
        self.listener = QtListener(name=name,
                                   host=host, port=port,
                                   data_port=data_port,
                                   logger=logger)
        self.listener.signals.message.connect(self.message_received)
        try:
            self.listener.signals.name_changed.connect(self.show_namespace_information)
            self.listener.signals.name_changed.connect(self.publisher.set_full_name)
        except AttributeError:
            pass  # for older pyleco versions.
        self.listener.start_listen()
        self.communicator = self.listener.get_communicator()  # type: ignore

        # Connect actions to slots. These actions have to be defined in the UI file.
        self._make_connections()

    def _setup_ui(self):
        raise NotImplementedError

    def _make_connections(self):
        self.actionClose.triggered.connect(self.close)
        self.actionSettings.triggered.connect(self.openSettings)

    @Slot()
    def openSettings(self) -> None:
        """Open the settings dialogue and apply changed settings."""
        settings_dialog = self.settings_dialog_class()
        if settings_dialog.exec():
            self.setSettings()

    def setSettings(self) -> None:
        """Apply new settings."""
        # TODO apply changes to variables.
        # settings = QtCore.QSettings()

    # On closure
    def closeEvent(self, event: QtCore.QEvent) -> None:
        self.stop_listen()
        # accept the close event (reject it, if you want to do something else)
        event.accept()

    def stop_listen(self) -> None:
        """Stop to listen for incoming messages."""
        self.listener.stop_listen()

    @Slot(Message)
    def message_received(self, message: Message):
        """Handle a message received (either a response or unsolicited)."""
        log.warning(f"Received an unhandled message: {message}")

    # @Slot(str)
    def show_namespace_information(self, full_name: str):
        """Show information regarding the namespace."""
        if "." in full_name:
            namespace = full_name.split('.')[0]
            self.statusBar().showMessage(f"Signed in to namespace '{namespace}'.", 5000)  # type: ignore  # noqa
        else:
            self.statusBar().showMessage("Not signed in.", 5000)  # type: ignore


class LECOBaseMainWindowDesigner(_LECOBaseMainWindow):
    """Base MainWindow subclass with a LECO listener, UI defined via designer ui file."""

    def __init__(self,
                 name: str,
                 ui_file_name: str,
                 settings_dialog_class: type[QtWidgets.QDialog] | None = None,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: logging.Logger = log,
                 data_port: int = PROXY_SENDING_PORT,
                 **kwargs) -> None:
        self._ui_file_name = ui_file_name
        super().__init__(name=name,
                         settings_dialog_class=settings_dialog_class,
                         host=host,
                         port=port,
                         logger=logger,
                         data_port=data_port,
                         **kwargs)

    def _setup_ui(self):
        uic.load_ui.loadUi(f"data/{self._ui_file_name}.ui", self)


class LECOBaseMainWindowNoDesigner(_LECOBaseMainWindow):
    """Base window, which is defined by manual design."""

    def _setup_ui(self):
        self.actionClose = QtGui.QAction("Close")  # type: ignore
        self.actionSettings = QtGui.QAction("Settings...")  # type: ignore
        mb = self.menuBar()
        if mb is not None:
            app_m = mb.addMenu("Application")
            app_m.addActions([self.actionSettings, self.actionClose])  # type: ignore


def start_app(main_window_class, window_kwargs: dict | None = None,
              logger: Optional[logging.Logger] = None,
              **kwargs) -> None:
    """Start a Qt App reading command line parameters."""
    doc = main_window_class.__doc__
    kwargs.setdefault('parser_description', doc.split(":param", maxsplit=1)[0] if doc else None)
    parsed_kwargs = parse_command_line_parameters(logger=logger, **kwargs)
    if window_kwargs is None:
        window_kwargs = parsed_kwargs
    else:
        window_kwargs.update(parsed_kwargs)
    app = QtWidgets.QApplication([])  # create an application
    # start the first widget, the main window:
    mainwindow = main_window_class(**window_kwargs)  # noqa: F841
    app.exec()  # start the application with its Event loop
