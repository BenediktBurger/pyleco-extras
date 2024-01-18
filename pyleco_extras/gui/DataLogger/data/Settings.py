"""
Module for the DataLogger settings.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Moneke
"""

from qtpy import QtCore, QtWidgets, uic
from qtpy.QtCore import Slot as pyqtSlot


class Settings(QtWidgets.QDialog):
    """Define the settings dialog and its methods."""

    def __init__(self, *args, **kwargs):
        """Initialize the dialog."""
        # Use initialization of parent class QDialog.
        super().__init__(*args, **kwargs)

        # Load the user interface file and show it.
        uic.load_ui.loadUi("data/Settings.ui", self)
        self.show()

        # Configure settings.
        self.settings = QtCore.QSettings()
        # Convenience list for widgets with value(), setValue() methods.
        self.sets = (
            # widget name, key of setting, defaultValue, type of defaultValue
            (self.sbAutoSaveInterval, 'autoSaveInterval', 60, int),
            (self.sbDataLengthLimit, "dataLengthLimit", 0, int),
            # (self.leSavePath, 'savePath', "", str),
            #   Plot options
            (self.sbAutoCut, 'autoCut', 200, int),
            # (self.cbGrid, 'grid', False, bool),
        )
        self.readValues()

        # CONNECT BUTTONS.
        # Define RestoreDefaults button and connect it.
        self.pbRestoreDefaults = self.buttonBox.button(
            QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults)
        self.pbRestoreDefaults.clicked.connect(self.restoreDefaults)
        self.pbSavePath.clicked.connect(self.openFileDialog)

    @pyqtSlot()
    def readValues(self):
        """Read the stored values and show them on the user interface."""
        for setting in self.sets:
            widget, name, value, typ = setting
            widget.setValue(self.settings.value(name, defaultValue=value,
                                                type=typ))
        self.leSavePath.setText(self.settings.value('savePath', type=str))
        self.cbGrid.setChecked(self.settings.value('grid', type=bool))

    @pyqtSlot()
    def restoreDefaults(self):
        """Restore the user interface to default values."""
        for setting in self.sets:
            widget, name, value, typ = setting
            widget.setValue(value)

    @pyqtSlot()
    def accept(self):
        """Save the values from the user interface in the settings."""
        # is executed, if pressed on a button with the accept role
        for setting in self.sets:
            widget, name, value, typ = setting
            self.settings.setValue(name, widget.value())
        self.settings.setValue('savePath', self.leSavePath.text())
        self.settings.setValue('grid', self.cbGrid.isChecked())
        super().accept()  # make the normal accept things

    def openFileDialog(self):
        """Open a file path dialog."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Save path")
        self.leSavePath.setText(path)
