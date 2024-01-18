"""
Module for the Settings dialog class.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Moneke
"""

from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtCore import pyqtSlot


class Settings(QtWidgets.QDialog):
    """Define the settings dialog and its methods."""

    def __init__(self):
        """Initialize the dialog."""
        # Use initialization of parent class QDialog.
        super().__init__()

        # Load the user interface file and show it.
        uic.loadUi("data/Settings.ui", self)
        self.show()

        # Configure settings.
        self.settings = QtCore.QSettings()
        # Convenience list for widgets with value(), SetValue() methods.
        self.sets = (
            # name of widget, key of setting, defaultValue, type of data
            # (self.widget, 'name', 0, int),
            (self.sbStarterPort, 'starterPort', 11111, int),
            # TODO add your widgets.
        )
        self.readValues()

        # CONNECT BUTTONS.
        # Define RestoreDefaults button and connect it.
        restore = QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults
        self.pbRestoreDefaults = self.buttonBox.button(restore)
        self.pbRestoreDefaults.clicked.connect(self.restoreDefaults)
        # self.pbSavePath.clicked.connect(self.openFileDialog)

    @pyqtSlot()
    def readValues(self):
        """Read the stored values and show them on the user interface."""
        for widget, name, value, typ in self.sets:
            widget.setValue(self.settings.value(name, defaultValue=value,
                                                type=typ))
        # self.leSavePath.setText(self.settings.value('tasksPath', "tasks", type=str))

    @pyqtSlot()
    def restoreDefaults(self):
        """Restore the user interface to default values."""
        for widget, name, value, typ in self.sets:
            widget.setValue(value)
        # self.leSavePath.setText("tasks")

    @pyqtSlot()
    def accept(self):
        """Save the values from the user interface in the settings."""
        # is executed, if pressed on a button with the accept role
        for widget, name, value, typ in self.sets:
            self.settings.setValue(name, widget.value())
        # self.settings.setValue('tasksPath', self.leSavePath.text())
        super().accept()  # make the normal accept things

    # def openFileDialog(self):
    #     """Open a file path dialog."""
    #     path = QtWidgets.QFileDialog.getExistingDirectory(self, "Tasks path")
    #     self.leSavePath.setText(path)
