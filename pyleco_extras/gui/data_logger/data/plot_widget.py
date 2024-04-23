"""
Plot window of the Datalogger.

Created on Fri Jul  9 14:32:56 2021 by Benedikt Burger.
"""

import logging
import math
from typing import Any, Iterable, Protocol, Optional

import numpy as np
import pint
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Slot as pyqtSlot  # type: ignore


class DataLoggerGuiProtocol(Protocol):
    current_units: dict[str, str]
    timer: QtCore.QTimer

    def get_data(
        self, key: str, start: Optional[int] = None, stop: Optional[int] = None
    ) -> list[float]: ...

    def get_xy_data(
        self,
        y_key: str,
        x_key: Optional[str] = None,
        start: Optional[int] = None,
        stop: Optional[int] = None,
    ) -> tuple[list[float]] | tuple[list[float], list[float]]: ...

    def get_data_keys(self) -> Iterable[str]: ...


class PlotGroupWidget(QtWidgets.QWidget):
    """Abstract class for the plot widgets."""

    def __init__(
        self,
        parent: DataLoggerGuiProtocol,
        autoCut: int = 0,
        grid: bool = False,
        log: Optional[logging.Logger] = None,
        **kwargs,
    ):
        super().__init__()
        self._setup_actions()
        self._setup_ui()
        self._layout()
        self.show()
        self.main_window = parent
        self.parent = parent  # type: ignore
        self.autoCut = autoCut
        self.sbAutoCut.setValue(autoCut)

        if log is None:
            self.log = logging.getLogger(__name__)
        else:
            self.log = log.getChild("Plot")

        # Configure comboboxes and plot.
        self.plotWidget.showGrid(x=grid, y=grid)
        self.setup_plot()
        self.keys = ["index", ""]
        self.getXkeys()
        self.getYkeys()

        self.restore_configuration(configuration=kwargs)

        self.setX()

    def _setup_actions(self) -> None:
        """Set up all the actions."""
        self.action_show_toolbar = QtGui.QAction("Show toolbar")  # type: ignore
        self.action_show_toolbar.setIconText("tb")
        self.action_show_toolbar.setToolTip("Show the toolbar (Ctrl + D).")
        self.action_show_toolbar.setCheckable(True)
        self.action_show_toolbar.setShortcut("Ctrl+D")
        self.actionly = QtGui.QAction("Show yellow line")  # type: ignore
        self.actionly.setIconText("ly")
        self.actionly.setToolTip("Show a yellow line.")
        self.actionly.setCheckable(True)
        self.actionlg = QtGui.QAction("Show green line")  # type: ignore
        self.actionlg.setIconText("lg")
        self.actionlg.setToolTip("Show a green line.")
        self.actionlg.setCheckable(True)
        self.actionv = QtGui.QAction("Large value font")  # type: ignore
        self.actionv.setIconText("v")
        self.actionv.setToolTip("Show the value with a larger fontsize.")
        self.actionv.setCheckable(True)
        self.actionvls = QtGui.QAction("Show vertical lines")  # type: ignore
        self.actionvls.setIconText("||")
        self.actionvls.setToolTip("Show vertical lines.")
        self.actionvls.setCheckable(True)
        self.actionEvaluate = QtGui.QAction("Evaluate data")  # type: ignore
        self.actionEvaluate.setIconText("ev")
        self.actionEvaluate.setToolTip("Evaluate the data.")
        self.actionEvaluate.setCheckable(True)

        # Connect actions to slots
        self.actionly.toggled.connect(self.toggleLineY)
        self.actionlg.toggled.connect(self.toggleLineG)
        self.actionv.toggled.connect(self.toggleV)
        self.actionvls.toggled.connect(self.toggleVerticalLines)
        self.actionEvaluate.toggled.connect(self.evaluate_data)

    def _setup_ui(self) -> None:
        """Generate the UI elements."""
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.addAction(self.actionlg)
        self.plotWidget.addAction(self.actionly)
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setVisible(False)
        self.menu = QtWidgets.QMenu()
        self.pbOptions = QtWidgets.QToolButton()
        self.pbOptions.setText("...")
        self.pbOptions.setToolTip("Show plot options.")
        self.bbX = QtWidgets.QComboBox()
        self.bbX.setMaxVisibleItems(15)
        self.bbX.setToolTip("X axis.")
        self.sbAutoCut = QtWidgets.QSpinBox()
        self.sbAutoCut.setMaximum(100000)
        self.sbAutoCut.setToolTip("Show the last number of values. If 0, show all values.")
        self.lbValue = QtWidgets.QLabel("last value")
        self.lbValue.setToolTip("Last value of the current axis.")
        self.lbValue.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )  # noqa

        self.lbEvaluation = QtWidgets.QLabel("-")
        self.lbEvaluation.setToolTip("Mean and standard deviation of the value in the limits.")

        # # Connect widgets to slots
        self.bbX.activated.connect(self.setX)
        self.sbAutoCut.valueChanged.connect(self.setAutoCut)
        self.pbOptions.clicked.connect(self.show_menu)
        self.actionEvaluate.toggled.connect(self.lbEvaluation.setVisible)
        self.action_show_toolbar.toggled.connect(self.toolbar.setVisible)

    def _layout(self) -> None:
        """Organize the elements into a layout."""
        raise NotImplementedError

    def setup_plot(self) -> None:
        """Configure the plotting area."""
        self.plotWidget.setLabel("bottom", "index")

    def closeEvent(self, event) -> None:
        """Close the plot."""
        try:
            self.main_window.timer.timeout.disconnect(self.update)
            self.main_window.signals.closing.disconnect(self.close)  # type: ignore
        except TypeError:
            pass  # Already disconnected.
        self.clear_plot()
        event.accept()

    def get_configuration(self) -> dict[str, Any]:
        """Get the current plot configuration."""
        configuration = {
            "type": type(self).__name__,
            "x_key": self.bbX.currentText(),
            "autoCut": self.autoCut,
            "ly": self.lineY.value() if self.actionly.isChecked() else False,
            "lg": self.lineG.value() if self.actionlg.isChecked() else False,
            "vls": (self.lineV1.value(), self.lineV2.value())
            if self.actionvls.isChecked()
            else False,  # noqa
            "evaluation": self.actionEvaluate.isChecked(),
        }
        return configuration

    def restore_configuration(self, configuration: dict[str, Any]) -> None:
        for key, value in configuration.items():
            if key == "x_key":
                self.bbX.setCurrentText(value)
            elif key == "autoCut":
                self.sbAutoCut.setValue(value)
            elif key == "ly":
                if value is not False:
                    self.toggleLineY(True, start=value)
                    self.actionly.setChecked(True)
            elif key == "lg":
                if value is not False:
                    self.toggleLineG(True, start=value)
                    self.actionlg.setChecked(True)
            elif key == "vls":
                if value is not False:
                    self.toggleVerticalLines(True, *value)
                    self.actionvls.setChecked(True)
            elif key == "evaluation":
                self.actionEvaluate.setChecked(value)

    @pyqtSlot()
    def update(self) -> None:
        """Update the plots."""
        raise NotImplementedError

    def clear_plot(self) -> None:
        """Clear the plots."""
        raise NotImplementedError

    def show_menu(self) -> None:
        self.menu.popup(self.pbOptions.mapToGlobal(QtCore.QPoint(0, 0)))

    def generate_axis_label(self, key: str) -> str:
        """Get the units string of `key`."""
        units = self.main_window.current_units.get(key, None)
        if units is None:
            return key
        elif isinstance(units, str):
            return f"{key} ({units})"
        elif isinstance(units, pint.Quantity):
            return f"{key} ({units:~})"
        else:
            return f"{key} ({units})"

    def setKeyNames(self, comboBox: QtWidgets.QComboBox) -> None:
        """Set the names for the `comboBox`."""
        current = comboBox.currentText()
        comboBox.clear()
        if comboBox == self.bbX:
            comboBox.addItem("index")
        comboBox.addItems(self.main_window.get_data_keys())
        comboBox.setCurrentText(current)

    def getXkeys(self) -> None:
        """Get the available keys for the x axis."""
        self.setKeyNames(self.bbX)

    @pyqtSlot()
    def setX(self) -> None:
        """Adjust the current x label."""
        text = self.bbX.currentText()
        self.keys[0] = text
        self.plotWidget.setLabel("bottom", text=self.generate_axis_label(text))
        self.update()

    def getYkeys(self) -> None:
        """Get the available keys for the y axis."""
        raise NotImplementedError()

    @pyqtSlot(int)
    def setAutoCut(self, value: int) -> None:
        """Set the current auto cut value."""
        self.autoCut = value

    @pyqtSlot()
    def updateKeys(self) -> None:
        """Update the combobox keys."""
        self.getXkeys()
        self.getYkeys()

    # Action slots
    @pyqtSlot(bool)
    def toggleLineY(self, checked: bool, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineY.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineY: pg.InfiniteLine = self.plotWidget.addLine(
                    y=start, pen="y", movable=True
                )

    @pyqtSlot(bool)
    def toggleLineG(self, checked: bool, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineG.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineG: pg.InfiniteLine = self.plotWidget.addLine(
                    y=start, pen="g", movable=True
                )

    @pyqtSlot(bool)
    def toggleVerticalLines(self, checked: bool, l1: float = 0, l2: float = 1) -> None:
        try:
            self.lineV1.setVisible(checked)
            self.lineV2.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineV1: pg.InfiniteLine = self.plotWidget.addLine(x=l1, pen="y", movable=True)
                self.lineV1.sigDragged.connect(self.evaluate_data)
                self.lineV2: pg.InfiniteLine = self.plotWidget.addLine(x=l2, pen="y", movable=True)
                self.lineV2.sigDragged.connect(self.evaluate_data)
        if not checked and not self.actionEvaluate.isChecked():
            self.lbEvaluation.setText("-")

    @pyqtSlot(bool)
    def toggleV(self, checked: bool) -> None:
        """Make the font size large."""
        font = QtGui.QFont()
        if checked:
            font.setPointSize(48)
            self.lbValue.setFont(font)
        else:
            self.lbValue.setFont(font)

    def evaluate_data(self, value: int = 0) -> None:
        x_key, y_key = self.keys
        if self.actionvls.isChecked():
            l1: int = self.lineV1.value()  # type: ignore
            l2: int = self.lineV2.value()  # type: ignore
            l1, l2 = sorted((l1, l2))
            if x_key == "index":
                raw_data = self.main_window.get_data(y_key, start=-self.autoCut)
                start = max(math.floor(l1), 0)
                stop = math.ceil(l2) + 1
                data = raw_data[start:stop]
            else:
                # TODO only from visible data or all data (as is now)?
                raw_x, raw_data = self.main_window.get_xy_data(y_key=y_key, x_key=x_key)
                raw_data = np.array(raw_data)
                raw_x = np.array(raw_x)
                data = raw_data[(l1 <= raw_x) * (raw_x <= l2)]
        else:
            data = self.main_window.get_data(y_key, start=-self.autoCut)
        mean = np.nanmean(a=data)
        std = np.nanstd(a=data)
        self.lbEvaluation.setText(f"({mean:g}\u00b1{std:g})")
