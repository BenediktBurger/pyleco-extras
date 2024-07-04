import logging
from pathlib import Path
from typing import Any, Optional, Union

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

    def __init__(
        self,
        name: str,
        settings_dialog_class: Optional[type[QtWidgets.QDialog]] = None,
        host: str = "localhost",
        port: int = COORDINATOR_PORT,
        logger: logging.Logger = log,
        data_port: int = PROXY_SENDING_PORT,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        # Load the user interface file and show it.
        self._setup_ui()
        self.setWindowTitle(name)
        self.show()
        if settings_dialog_class is not None:
            self.settings_dialog_class = settings_dialog_class

        # Set the application name
        if app := QtCore.QCoreApplication.instance():
            app.setOrganizationName("NLOQO")
            app.setApplicationName(name)

        # create the listener and the communicator
        self.publisher = DataPublisher(full_name=name, host=host)
        self.listener = QtListener(
            name=name, host=host, port=port, data_port=data_port, logger=logger
        )
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

    # LECO slots
    @Slot(Message)
    def message_received(self, message: Message) -> None:
        """Handle a message received (either a response or unsolicited)."""
        log.warning(f"Received an unhandled message: {message}")

    @Slot(str)
    def show_namespace_information(self, full_name: str) -> None:
        """Show information regarding the namespace."""
        if "." in full_name:
            namespace = full_name.split(".")[0]
            self.show_status_bar_message(f"Signed in to namespace '{namespace}'.", 5000)
        else:
            self.show_status_bar_message("Not signed in.", 5000)

    # Generic methods
    def show_status_bar_message(self, message: str, msecs: int = 0) -> None:
        """Show `message` in the statusbar for `timeout` ms (0 means until next message)."""
        self.statusBar().showMessage(message, msecs)  # type: ignore


class LECOBaseMainWindowDesigner(_LECOBaseMainWindow):
    """Base MainWindow subclass with a LECO listener, UI defined via designer ui file.

    :param name: Leco name
    :param ui_file_name: Name of the ui_file (without ".ui" termination)
    :param ui_file_path: Path to the ui file. Relative "data" or absolute, e.g.
        `pathlib.Path(__file__).parent / "data"`.
    """

    def __init__(
        self,
        name: str,
        ui_file_name: str,
        ui_file_path: Union[Path, str] = "data",
        settings_dialog_class: Optional[type[QtWidgets.QDialog]] = None,
        host: str = "localhost",
        port: int = COORDINATOR_PORT,
        logger: logging.Logger = log,
        data_port: int = PROXY_SENDING_PORT,
        **kwargs,
    ) -> None:
        if isinstance(ui_file_path, str):
            ui_file_path = Path(ui_file_path)
        self._file_path = ui_file_path / f"{ui_file_name}.ui"
        super().__init__(
            name=name,
            settings_dialog_class=settings_dialog_class,
            host=host,
            port=port,
            logger=logger,
            data_port=data_port,
            **kwargs,
        )

    def _setup_ui(self):
        uic.load_ui.loadUi(self._file_path, self)


class LECOBaseMainWindowNoDesigner(_LECOBaseMainWindow):
    """Base window, which is defined by manual design."""

    def _setup_ui(self) -> None:
        self.actionClose = QtGui.QAction("Close")  # type: ignore
        self.actionSettings = QtGui.QAction("Settings...")  # type: ignore
        mb = self.menuBar()
        if mb is not None:
            app_m = mb.addMenu("Application")
            app_m.addActions([self.actionSettings, self.actionClose])  # type: ignore


def start_app(
    main_window_class,
    window_kwargs: Optional[dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs,
) -> None:
    """Start a Qt App reading command line parameters."""
    doc = main_window_class.__doc__
    kwargs.setdefault("parser_description", doc.split(":param", maxsplit=1)[0] if doc else None)
    parsed_kwargs = parse_command_line_parameters(logger=logger, **kwargs)
    if window_kwargs is None:
        window_kwargs = parsed_kwargs
    else:
        window_kwargs.update(parsed_kwargs)
    app = QtWidgets.QApplication([])  # create an application
    # start the first widget, the main window:
    mainwindow = main_window_class(**window_kwargs)  # noqa: F841
    app.exec()  # start the application with its Event loop
