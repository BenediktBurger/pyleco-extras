# -*- coding: utf-8 -*-
"""
Plot window of the Datalogger.

Created on Fri Jul  9 14:32:56 2021 by Benedikt Burger.
"""

from typing import Any

import numpy as np
import pyqtgraph as pg
from qtpy import QtGui, QtWidgets
from qtpy.QtCore import Slot as pyqtSlot, Qt  # type: ignore

from .plotWidget import PlotGroupWidget, DataLoggerGuiProtocol


class SinglePlotWidget(PlotGroupWidget):
    """Window showing a plot.

    :param parent: Parent window.
    :param int autoCut: How many data points to show.
    :param bool grid: Whether to show a grid.
    :param logger log: Parent logger to handle log entries. Creates the child 'Plot'.
    """

    def __init__(self, parent: DataLoggerGuiProtocol, autoCut=0, grid=False, log=None, **kwargs):
        super().__init__(parent=parent, autoCut=autoCut, grid=grid, log=log, **kwargs)

        self.log.info("Plot created.")

    def _setup_toolbar(self):
        self.toolbar = QtWidgets.QToolBar(self)
        self.actionDots = QtGui.QAction(".")  # type: ignore
        self.actionDots.setToolTip("Show dots instead of lines.")
        self.actionly = QtGui.QAction("ly")  # type: ignore
        self.actionly.setToolTip("Show a yellow line.")
        self.actionlg = QtGui.QAction("lg")  # type: ignore
        self.actionlg.setToolTip("Show a green line.")
        self.actionmm = QtGui.QAction("mm")  # type: ignore
        self.actionmm.setToolTip("Show red, dashed lines for global min and max.")
        self.actionlmm = QtGui.QAction("lmm")  # type: ignore
        self.actionlmm.setToolTip("Show orange, dashed lines for local min and max.")
        self.actionv = QtGui.QAction("v")  # type: ignore
        self.actionv.setToolTip("Show the value with a larger fontsize.")
        for action in (self.actionDots, self.actionly, self.actionlg, self.actionmm,
                       self.actionlmm, self.actionv):
            action.setCheckable(True)
            self.toolbar.addAction(action)
        self.toolbar.setVisible(False)

        # # Connect actions to slots
        self.actionDots.toggled.connect(self.setStyle)
        self.actionly.toggled.connect(self.toggleLineY)
        self.actionlg.toggled.connect(self.toggleLineG)
        self.actionmm.toggled.connect(self.toggleMM)
        self.actionlmm.toggled.connect(self.toggleLMM)
        self.actionv.toggled.connect(self.toggleV)

    def _setup_ui(self):
        self._setup_toolbar()
        super()._setup_ui()
        self.bbY = QtWidgets.QComboBox()
        self.bbY.setMaxVisibleItems(15)
        self.bbY.setToolTip("Y axis.")

        # # Connect widgets to slots
        self.bbY.activated.connect(self.setY)
        self.pbOptions.toggled.connect(self.toolbar.setVisible)

    def _layout(self):
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(1)
        vbox.setContentsMargins(0, 0, 0, 0)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(2)
        hbox.setContentsMargins(0, 0, 0, 0)
        for widget in (self.pbOptions, self.bbY, self.bbX, self.sbAutoCut, self.lbValue):
            hbox.addWidget(widget)

        vbox.addWidget(self.toolbar)
        vbox.addWidget(self.plotWidget)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def setup_plot(self):
        """Configure the plot."""
        super().setup_plot()
        self.reference = self.plotWidget.plot([], [])
        self.plotWidget.setLabel('left', "None")

    def get_configuration(self) -> dict[str, Any]:
        """Get the current plot configuration."""
        configuration = super().get_configuration()
        configuration.update({
            "y_key": self.bbY.currentText(),
            "dots": self.actionDots.isChecked(),
            "lmm": self.actionlmm.isChecked(),
            "mm": self.actionmm.isChecked(),
            "ly": self.lineY.value() if self.actionly.isChecked() else False,
            "lg": self.lineG.value() if self.actionlg.isChecked() else False,
        })
        return configuration

    def restore_configuration(self, configuration: dict[str, Any]) -> None:
        super().restore_configuration(configuration=configuration)
        for key, value in configuration.items():
            if key == "y_key":
                self.bbY.setCurrentText(value)
            elif key == "dots":
                self.actionDots.setChecked(value)
            elif key == "lmm":
                self.actionlmm.setChecked(value)
            elif key == "mm":
                self.actionmm.setChecked(value)
            elif key == "ly":
                if value is not False:
                    self.toggleLineY(True, start=value)
                    self.actionly.setChecked(True)
            elif key == "lg":
                if value is not False:
                    self.toggleLineG(True, start=value)
                    self.actionlg.setChecked(True)
        self.setY()

    @pyqtSlot()
    def update(self):
        """Update the plots."""
        x_key, y_key = self.keys
        try:
            if x_key == 'index':
                self.reference.setData(
                    self.main_window.lists[y_key][-self.autoCut:])
            else:
                self.reference.setData(
                    self.main_window.lists[x_key][-self.autoCut:],
                    self.main_window.lists[y_key][-self.autoCut:])
            if self.actionmm.isChecked():
                l1, l2 = self.linesMM
                l1.setValue(np.nanmin(self.main_window.lists[y_key]))
                l2.setValue(np.nanmax(self.main_window.lists[y_key]))
            if self.actionlmm.isChecked():
                l1, l2 = self.linesLMM
                l1.setValue(np.nanmin(self.main_window.lists[y_key][-self.autoCut:]))
                l2.setValue(np.nanmax(self.main_window.lists[y_key][-self.autoCut:]))
            try:
                value = self.main_window.lists[y_key][-1]
            except (IndexError, KeyError):
                value = float("nan")
            self.lbValue.setText(f"{value:.8g} {self.main_window.current_units.get(y_key, '')}")
        except KeyError:
            pass  # no data
        except ValueError:
            try:
                self.lbValue.setText(f"{y_key}: {self.main_window.lists[y_key][-1]}")
            except IndexError:
                self.lbValue.setText("IndexError")

    def clear_plot(self):
        """Clear the plot area to reduce memory."""
        self.reference.setData([])

    @pyqtSlot(bool)
    def setStyle(self, checked: bool):
        """Set the current plot style."""
        if checked:
            self.reference.setPen(None)
            self.reference.setSymbol("o")
            self.reference.setSymbolSize(5)
        else:
            self.reference.setPen(.9)
            self.reference.setSymbol(None)

    @pyqtSlot(bool)
    def toggleLineY(self, checked, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineY.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineY = self.plotWidget.addLine(y=start, pen='y', movable=True)

    @pyqtSlot(bool)
    def toggleLineG(self, checked: bool, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineG.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineG = self.plotWidget.addLine(y=start, pen='g', movable=True)

    @pyqtSlot(bool)
    def toggleMM(self, checked: bool):
        """Add lines for global min and max."""
        if checked:
            pen = pg.mkPen("red", style=Qt.PenStyle.DashLine)
            l1: pg.InfiniteLine = self.plotWidget.addLine(y=0, pen=pen)
            l2: pg.InfiniteLine = self.plotWidget.addLine(y=0, pen=pen)
            self.linesMM = (l1, l2)
        else:
            for line in self.linesMM:
                self.plotWidget.removeItem(line)

    @pyqtSlot(bool)
    def toggleLMM(self, checked: bool):
        """Add lines for global min and max."""
        if checked:
            pen = pg.mkPen("orange", style=Qt.PenStyle.DashLine)
            l1: pg.InfiniteLine = self.plotWidget.addLine(y=0, pen=pen)
            l2: pg.InfiniteLine = self.plotWidget.addLine(y=0, pen=pen)
            self.linesLMM = (l1, l2)
        else:
            for line in self.linesLMM:
                self.plotWidget.removeItem(line)

    @pyqtSlot(bool)
    def toggleV(self, checked: bool) -> None:
        """Make the font size large."""
        font = QtGui.QFont()
        if checked:
            font.setPointSize(48)
            self.lbValue.setFont(font)
        else:
            self.lbValue.setFont(font)

    def getYkeys(self):
        """Get the available keys for the y axis."""
        self.setKeyNames(self.bbY)

    @pyqtSlot()
    def setY(self):
        """Adjust the current y label."""
        text = self.bbY.currentText()
        self.keys[1] = text
        self.plotWidget.setLabel('left', text=self.generate_axis_label(text))
        self.update()
