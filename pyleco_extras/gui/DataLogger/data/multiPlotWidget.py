# -*- coding: utf-8 -*-
"""
Plot window of the Datalogger.

Created on Fri Jul  9 14:32:56 2021 by Benedikt Burger.
"""

from typing import Any

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Slot as pyqtSlot, Qt  # type: ignore

import pyqtgraph as pg


from .plotWidget import PlotGroupWidget, DataLoggerGuiProtocol


class MultiPlotWidget(PlotGroupWidget):
    """Window showing a plot.

    :param parent: Parent window.
    :param int autoCut: How many data points to show.
    :param bool grid: Whether to show a grid.
    :param str name: Name to show as window title.
    :param logger log: Parent logger to handle log entries. Creates the child 'PlotMulti'.
    """

    def __init__(self, parent: DataLoggerGuiProtocol, autoCut=0, grid=False, log=None,
                 **kwargs) -> None:
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["pen", "key"])
        self.model.dataChanged.connect(self.lineConfigurationChanged)
        self.lines = {}  # The lines themselves. key: line
        self.pens = {}  # Pen names for restoring them. key: pen name
        self.legend_entries = {}  # lines for the legend. key: legend line
        self.references = {}  # key: axis index

        super().__init__(parent=parent, autoCut=autoCut, grid=grid, log=log, **kwargs)

        self.tvLines.setModel(self.model)
        self._adjustView()
        sm = self.tvLines.selectionModel()  # selection model
        sm.currentChanged.connect(self.showValues)

        self.log.info("MultiPlot created.")

    def _setup_actions(self):
        super()._setup_actions()
        self.action_show_lines = QtGui.QAction("ls")
        self.action_show_lines.setToolTip("Show the lines setup.")
        self.action_show_lines.setCheckable(True)
        self.action_show_lines.triggered.connect(self.show_line_settings)

    def _setup_ui(self):
        super()._setup_ui()
        for action in (self.actionlg, self.actionly, self.actionv, self.action_show_lines,
                       self.actionvls, self.actionEvaluate,):
            self.toolbar.addAction(action)
        self.tvLines = QtWidgets.QTableView()
        self.tvLines.setToolTip('<html><head/><body><p>Select the color of the key to show. Either '
                                'as a name or as RGB.</p><p>Prefix &quot;n,&quot; to show it to '
                                'the n<span style=" vertical-align:super;">th</span> right axis.'
                                '</p><p>Only the main axis and the first right axis get plot '
                                'transforms and &quot;view all&quot; via the &quot;A&quot; button.'
                                '</p></body></html>')
        self.tvLines.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self.tvLines.verticalHeader().setVisible(False)
        self.pbAutoRange = QtWidgets.QToolButton()
        self.pbAutoRange.setText("A")
        self.pbAutoRange.setToolTip("Set all axes to auto Y range (Ctrl + A).")
        self.pbAutoRange.setShortcut("Ctrl+A")
        # self.bbX: minimum size 90x0
        self.pbLines = QtWidgets.QToolButton()
        self.pbLines.setText("ls")
        self.pbLines.setToolTip("Show the lines setup.")
        self.pbLines.setCheckable(True)
        self.pbLines.clicked.connect(self.show_line_settings)

        # Connect actions to slots
        self.pbAutoRange.clicked.connect(self.setAutoRange)

    def _layout(self):
        display_box = QtWidgets.QHBoxLayout()
        display_box.setSpacing(1)
        display_box.setContentsMargins(0, 0, 0, 0)
        for widget in (self.plotWidget, self.tvLines):
            display_box.addWidget(widget)
        display_box.setStretchFactor(self.plotWidget, 10)

        button_box = QtWidgets.QHBoxLayout()
        button_box.setSpacing(1)
        button_box.setContentsMargins(0, 0, 0, 0)
        for widget in (self.pbOptions, self.pbAutoRange, self.bbX, self.sbAutoCut, self.lbValue,
                       self.lbEvaluation, self.pbLines,):
            button_box.addWidget(widget)
        button_box.setStretchFactor(self.bbX, 1)
        button_box.setStretchFactor(self.lbValue, 3)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(1)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.toolbar)
        vbox.addLayout(display_box)
        vbox.addLayout(button_box)
        self.setLayout(vbox)

    def setup_plot(self):
        """Configure the plot."""
        super().setup_plot()
        self.plotWidget.addLegend(brush=(255, 255, 255, 64), labelTextColor=.9,
                                  horSpacing=20, verSpacing=-10)
        plotItem = self.plotWidget.plotItem
        self.axes: list[pg.PlotItem] = [plotItem]
        plotItem.vb.sigResized.connect(self._updateViews)  # type: ignore

    def append_axis(self):
        """Add another axis."""
        p0 = self.axes[0]
        p = pg.ViewBox()
        p0.scene().addItem(p)
        number = len(self.axes)
        if number == 1:
            p0.showAxis("right")
            p0.getAxis("right").linkToView(p)
        else:
            ax = pg.AxisItem("right")
            p0.layout.addItem(ax, 2, number + 1)
            ax.linkToView(p)
            ax.setZValue(-10000)
        p.setXLink(p0)
        self.axes.append(p)

    @pyqtSlot()
    def _updateViews(self):
        """The view has changed, update the other axis."""
        for i in range(1, len(self.axes)):
            self.axes[i].setGeometry(self.axes[0].vb.sceneBoundingRect())  # type: ignore
            self.axes[i].linkedViewChanged(self.axes[0].vb, self.axes[i].XAxis)

    def get_lines(self) -> dict[str, str]:
        """Get all lines currently defined."""
        lines = {}
        for i in range(self.model.rowCount()):
            key = self.model.item(i, 1).data(Qt.ItemDataRole.DisplayRole)
            pen_color = self.model.item(i, 0).data(Qt.ItemDataRole.DisplayRole)
            lines[key] = pen_color
        return lines

    def set_lines(self, lines: dict[str, str]) -> None:
        """Set the lines definitions."""
        for i in range(self.model.rowCount()):
            key = self.model.item(i, 1).data(Qt.ItemDataRole.DisplayRole)
            pen_color = lines.get(key, "")
            self.model.item(i, 0).setData(pen_color, Qt.ItemDataRole.DisplayRole)

    def get_configuration(self) -> dict[str, Any]:
        """Get the current plot configuration."""
        configuration = super().get_configuration()
        configuration.update({
            "lines": self.get_lines(),
            "y_key": self.keys[1],
        })
        return configuration

    def restore_configuration(self, configuration: dict[str, Any]) -> None:
        super().restore_configuration(configuration=configuration)
        for key, value in configuration.items():
            if key == "y_key":
                self.keys[1] = value
        lines = configuration.get("lines")
        if lines is not None:
            self.set_lines(lines)
            self.show_line_settings(False)
        else:
            self.pbOptions.setChecked(True)

    @pyqtSlot()
    def update(self):
        """Update the plots."""
        x_key, y_key = self.keys
        try:
            if x_key == 'index':
                for key, line in self.lines.items():
                    line.setData(
                        self.main_window.lists[key][-self.autoCut:])
            else:
                for key, line in self.lines.items():
                    line.setData(
                        self.main_window.lists[x_key][-self.autoCut:],
                        self.main_window.lists[key][-self.autoCut:])
        except KeyError:
            return  # no data
        try:
            value = self.main_window.lists[y_key][-1]
            units = self.main_window.current_units.get(y_key, '')
            self.lbValue.setText(f"{y_key}: {value:.8g} {units}")
        except (IndexError, KeyError, TypeError):
            pass  # no data
        except ValueError:
            self.lbValue.setText(f"{y_key}: {self.main_window.lists[y_key][-1]}")
        if self.actionEvaluate.isChecked():
            self.evaluate_data()

    def clear_plot(self):
        """Clear plots."""
        for line in self.lines.values():
            line.setData([])

    @pyqtSlot()
    def setAutoRange(self):
        """Set all axes to automatic ranging."""
        for axis in self.axes:
            axis.enableAutoRange(axis="y")

    def getYkeys(self):
        """Get the available keys for the y axis."""
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["pen", "key"])
        keys = self.main_window.lists.keys()
        for key in keys:
            pen_color = self.pens.get(key, "")
            if pen_color and key not in self.lines:
                self.lines[key] = self.plotWidget.plot([], [], name=key, pen=pen_color)
            pen = QtGui.QStandardItem(pen_color)
            k = QtGui.QStandardItem(key)
            k.setEditable(False)
            self.model.appendRow([pen, k])
        for key, line in list(self.lines.items()):
            if key not in keys:
                self.plotWidget.removeItem(self.lines[key])
                del self.lines[key]
        self._adjustView()

    def lineConfigurationChanged(self, topLeft, bottomRight, roles):
        """Create/update lines according to changed data"""
        key = self.model.itemFromIndex(topLeft.siblingAtColumn(1)).data(Qt.ItemDataRole.DisplayRole)
        pen_color = self.model.itemFromIndex(topLeft).data(Qt.ItemDataRole.DisplayRole)
        if pen_color:
            parts = pen_color.split(",")
            try:
                pen = pg.mkPen(parts.pop())
            except ValueError:
                self.model.itemFromIndex(topLeft).setData("", Qt.ItemDataRole.DisplayRole)
                return
            self.pens[key] = pen_color
            axis = int(parts[0]) if parts else 0
            if key in self.lines:
                if axis == self.references.get(key, 0):
                    self.lines[key].setPen(pen)
                    if key in self.legend_entries:
                        self.legend_entries[key].setPen(pen)
                else:
                    self._removeLine(key)
                    self._addLine(key, axis, pen)
            else:
                self._addLine(key, axis, pen)
        elif key in self.lines:
            self._removeLine(key)
        self.update()

    def _addLine(self, key, axis, pen):
        """Add a line to the plot."""
        if axis > 0:
            while len(self.axes) < axis + 1:
                self.append_axis()
            line = pg.PlotCurveItem([], [], name=key, pen=pen)
            self.lines[key] = line
            self.axes[axis].addItem(line)  # type: ignore
            self.references[key] = axis
            self.legend_entries[key] = self.plotWidget.plot([], [],
                                                            name=f"{axis}: {key}",
                                                            pen=pen)
        else:
            self.lines[key] = self.plotWidget.plot([], [], name=key, pen=pen)

    def _removeLine(self, key):
        """Remove a line from the plot."""
        if key in self.legend_entries:
            self.axes[self.references[key]].removeItem(self.lines[key])  # type: ignore
            del self.references[key]
            self.plotWidget.removeItem(self.legend_entries[key])
            del self.legend_entries[key]
        else:
            self.plotWidget.removeItem(self.lines[key])
        del self.lines[key]
        del self.pens[key]

    def showValues(self, current, previous=None):
        """Show the values of the selected key."""
        if self.pbOptions.isChecked():
            self.keys[1] = self.model.item(current.row(), 1).data(Qt.ItemDataRole.DisplayRole)
            self._last_index = current

    def _adjustView(self):
        """Adjust the table view to the content."""
        self.tvLines.resizeColumnsToContents()

    @pyqtSlot(bool)
    def show_line_settings(self, checked: bool) -> None:
        """Restore the table view, once the "show" button is clicked."""
        self.tvLines.setVisible(checked)
        self.pbLines.setChecked(checked)
        if checked:
            try:
                self._adjustView()
            except Exception as exc:
                self.log.exception("Adjusting the view for showing the data failed.", exc_info=exc)
                return
            try:
                sm = self.tvLines.selectionModel()
                sm.select(self._last_index, sm.SelectionFlag.SelectCurrent)
            except AttributeError:
                pass  # if no last index, do not select any.
            except Exception as exc:
                self.log.exception("Selecting previous data failed.", exc_info=exc)
