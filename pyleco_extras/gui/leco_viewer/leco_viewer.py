from PyQt6 import QtCore, QtGui, QtWidgets

from pyleco.directors.coordinator_director import CoordinatorDirector

from pyleco_extras.gui_utils.base_main_window import LECOBaseMainWindowNoDesigner, start_app
from pyleco_extras.gui.leco_viewer.settings import Settings


class LECOViewer(LECOBaseMainWindowNoDesigner):
    """Show the known network structure with the Coordinators and Components."""

    def __init__(self, name: str = "CoordinatorViewer",
                 host: str = "localhost",
                 **kwargs) -> None:
        super().__init__(name,
                         settings_dialog_class=Settings,
                         host=host,
                         **kwargs)
        self._setup_model()

        self.director = CoordinatorDirector(communicator=self.communicator)

        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(QtCore.QByteArray(geometry))

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.read_coordinators)
        self.timer.start(1000)

    def _setup_ui(self) -> None:
        super()._setup_ui()
        self.tv = QtWidgets.QTreeView(parent=self)
        self.setCentralWidget(self.tv)

    def _setup_model(self) -> None:
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["LECO network"])
        self.tv.setModel(self.model)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Store the window geometry
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(a0)

    def setSettings(self) -> None:
        settings = QtCore.QSettings()
        self.timer.setInterval(settings.value("readoutInterval", 1, float))

    def add_coordinator(self, name: str) -> QtGui.QStandardItem:
        coordinator = QtGui.QStandardItem(name)
        self.model.invisibleRootItem().appendRow(coordinator)
        return coordinator

    def read_coordinators(self) -> None:
        try:
            global_components = self.director.get_global_components()
        except TimeoutError as exc:
            self.statusBar().showMessage(f"No response. {exc}")
            return
        iru = self.model.invisibleRootItem()
        while iru.hasChildren():
            iru.removeRow(0)
        for coordinator, components in global_components.items():
            c = self.add_coordinator(coordinator)
            c.appendRows([QtGui.QStandardItem(comp) for comp in sorted(components)])
            i = self.model.indexFromItem(c)
            self.tv.setExpanded(i, True)


if __name__ == "__main__":  # pragma: no cover
    start_app(LECOViewer)
