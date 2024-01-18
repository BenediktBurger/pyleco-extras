"""
Module for the Settings dialog class.

Created on 16.01.2024 by Benedikt Burger
"""

from typing import Any, Callable, Optional, Union

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Slot as pyqtSlot  # type: ignore


VALUE_WIDGETS = Union[
    QtWidgets.QSpinBox,
    QtWidgets.QDoubleSpinBox,
    QtWidgets.QAbstractSlider,
]


class BaseSettings(QtWidgets.QDialog):
    """Define the settings dialog and its methods.

    Define the form in :meth:`setup_form`.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the dialog."""
        # Use initialization of parent class QDialog.
        super().__init__(**kwargs)

        self.sets: list[tuple[VALUE_WIDGETS, str, Any, type]] = [
            # name of widget, key of setting, defaultValue, type of data
            # (self.widget, "name", 0, int),
        ]
        self.anyset: list[tuple[
            Callable[[], Any],  # getter
            Callable[[Any], None],  # setter
            str,  # key of setting
            Any,  # defaultValue
            type,  # type of data
            ]] = []

        # Load the user interface file and show it.
        self._setup_ui()
        self._connect_ui()
        self.show()

        # Configure settings.
        self.settings = QtCore.QSettings()
        # Convenience list for widgets with value(), SetValue() methods.
        self.readValues()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Settings")
        self.formLayout = QtWidgets.QFormLayout()
        self.setLayout(self.formLayout)
        self.setup_form(self.formLayout)
        # nötig buttonBox zu erstellen?
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults
        )
        self.formLayout.addRow(self.buttonBox)

    def _connect_ui(self) -> None:
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        restore = self.buttonBox.button(
            QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults)
        restore.clicked.connect(self.restoreDefaults)  # type: ignore

    def setup_form(self, layout: QtWidgets.QFormLayout) -> None:
        """Setup the layout of the Settings formular.

        You might use the :meth:`add_value_widget` and :meth:`add_widget` methods.
        """
        raise NotImplementedError

    def add_value_widget(
            self,
            labelText: Optional[str],
            widget: VALUE_WIDGETS,
            key: str,
            defaultValue: Any = 0,
            type: Any = float,
            ) -> None:
        """Add a widget which supports value/setValue.

        :param labelText: add to the form with this label. Do not add to the form (but to the sets)
            if it is None.
        """
        if labelText is not None:
            self.formLayout.addRow(labelText, widget)
        self.sets.append((widget, key, defaultValue, type))

    def add_widget(
            self,
            labelText: str,
            widget: QtWidgets.QWidget,
            getter: Callable[[], Any],
            setter: Callable[[Any], None],
            key: str,
            defaultValue: Any,
            type: Any,
            ) -> None:
        """Add a widget."""
        self.formLayout.addRow(labelText, widget)
        self.anyset.append((getter, setter, key, defaultValue, type))

    def create_file_dialog(self, default: str, tooltip: str = "") -> None:
        pbSavePath = QtWidgets.QPushButton("Open...")
        self.leSavePath = QtWidgets.QLineEdit()
        self.leSavePath.setToolTip(tooltip)
        self.formLayout.addRow(pbSavePath, self.leSavePath)

        @pyqtSlot()
        def openFileDialog() -> None:
            """Open a file path dialog."""
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Save path")
            self.leSavePath.setText(path)

        pbSavePath.clicked.connect(openFileDialog)

    def readValues(self) -> None:
        """Read the stored values and show them on the user interface."""
        for widget, name, value, typ in self.sets:
            widget.setValue(self.settings.value(name, defaultValue=value,
                                                type=typ))
        for getter, setter, name, value, typ in self.anyset:
            setter(self.settings.value(name, defaultValue=value, type=typ))
        try:
            self.leSavePath.setText(self.settings.value("savePath", type=str))
        except AttributeError:
            pass

    @pyqtSlot()
    def restoreDefaults(self) -> None:
        """Restore the user interface to default values."""
        for widget, name, value, typ in self.sets:
            widget.setValue(value)
        for getter, setter, name, value, typ in self.anyset:
            setter(value)

    @pyqtSlot()
    def accept(self) -> None:
        """Save the values from the user interface in the settings."""
        # is executed, if pressed on a button with the accept role
        for widget, name, value, typ in self.sets:
            self.settings.setValue(name, widget.value())
        for getter, setter, name, value, typ in self.anyset:
            self.settings.setValue(name, getter())
        try:
            self.settings.setValue("savePath", self.leSavePath.text())
        except AttributeError:
            pass
        super().accept()  # make the normal accept things
