"""
Module for the Settings dialog class.

Created on Thu Nov 26 19:02:38 2020 by Benedikt Moneke
"""

from qtpy import QtWidgets

from pyleco_extras.gui_utils.base_settings import BaseSettings


class Settings(BaseSettings):
    """Define the settings dialog and its methods."""

    def setup_form(self, layout: QtWidgets.QFormLayout) -> None:
        """Setup the layout of the Settings formular.

        You might use the :meth:`add_value_widget` method.
        """
        interval = QtWidgets.QDoubleSpinBox()
        interval.setSuffix(" s")
        interval.setRange(0.01, 1000)
        interval.setDecimals(2)
        interval.setToolTip("Interval between two readouts.")
        self.add_value_widget(
            labelText="Interval",
            widget=interval,
            key="readoutInterval",
            defaultValue=1,
        )
