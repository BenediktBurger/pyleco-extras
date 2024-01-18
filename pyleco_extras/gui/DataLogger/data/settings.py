"""
Module for the DataLogger settings.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Burger
"""

from qtpy import QtWidgets

from pyleco_extras.gui_utils.base_settings import BaseSettings


class Settings(BaseSettings):
    """Define the settings dialog and its methods."""

    def setup_form(self, layout: QtWidgets.QFormLayout) -> None:
        autoSave = QtWidgets.QSpinBox()
        autoSave.setToolTip("Interval between two automatic saves.")
        autoSave.setSuffix(" min")
        autoSave.setRange(6, 2880)
        autoSave.setSingleStep(6)
        self.add_value_widget("Auto save", autoSave, "autoSaveInterval", 60, int)

        dataLimit = QtWidgets.QSpinBox()
        dataLimit.setToolTip("Number of data points to keep at least in memory, if the data limit option is activated.")  # noqa
        dataLimit.setSuffix(" samples")
        dataLimit.setMaximum(100000)
        dataLimit.setSingleStep(1000)
        self.add_value_widget("Data limit", dataLimit, "dataLengthLimit", 0, int)

        self.create_file_dialog("")

        autoCut = QtWidgets.QSpinBox()
        autoCut.setToolTip("Default number of samples to show for new plots.")
        autoCut.setSuffix(" samples")
        autoCut.setMaximum(10000)
        autoCut.setSingleStep(10)
        self.add_value_widget("Auto cut", autoCut, "autoCut", 200, int)

        cbGrid = QtWidgets.QCheckBox("Start with grid")
        cbGrid.setToolTip("Start the plots with a grid.")
        self.add_widget("Grid", widget=cbGrid,
                        getter=cbGrid.isChecked,
                        setter=cbGrid.setChecked,
                        key="grid",
                        defaultValue=False,
                        type=bool,
                        )
