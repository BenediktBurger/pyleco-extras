"""
Module for the DataLogger Remote settings.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Burger
"""

from qtpy import QtWidgets
from pyleco_extras.gui_utils.base_settings import BaseSettings


class Settings(BaseSettings):
    """Define the settings dialog and its methods."""

    def setup_form(self, layout: QtWidgets.QFormLayout) -> None:
        name = QtWidgets.QLineEdit()
        name.setToolTip("Name of the data logger to control remotely.")
        self.add_widget("Name", name,
                        getter=name.text,
                        setter=name.setText,
                        key="remoteName",
                        defaultValue="",
                        type=str)

        dataLimit = QtWidgets.QSpinBox()
        dataLimit.setToolTip("Number of data points to keep at least in memory, if the data limit option is activated.")  # noqa
        dataLimit.setSuffix(" samples")
        dataLimit.setMaximum(100000)
        dataLimit.setSingleStep(1000)
        self.add_value_widget("Data limit", dataLimit, "dataLengthLimit", 0, int)

        follow = QtWidgets.QCheckBox("Follow each data point of the data logger.")
        follow.setToolTip("Follow each data point published by the data logger, otherwise, use the timer to request data points.")  # noqa
        self.add_widget("Follow", follow,
                        getter=follow.isChecked,
                        setter=follow.setChecked,
                        key="follow",
                        defaultValue=True,
                        type=bool)

        interval = QtWidgets.QSpinBox()
        interval.setToolTip("Readout interval requesting the latest datapoint, if not followed.")
        interval.setSuffix(" ms")
        interval.setRange(40, 1_000_000)
        interval.setSingleStep(10)
        self.add_value_widget("Interval", interval, "interval", 1000, int)
