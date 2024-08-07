# -*- coding: utf-8 -*-
"""
Plot window of the Datalogger.

Created on Fri Jul  9 14:32:56 2021 by Benedikt Burger.
"""

import logging
from typing import Any, Optional

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import Slot as pyqtSlot, Qt  # type: ignore

import pyqtgraph as pg


from .plot_widget import PlotGroupWidget, DataLoggerGuiProtocol


class MultiPlotWidget(PlotGroupWidget):
    """Window showing a plot.

    :param parent: Parent window.
    :param int autoCut: How many data points to show.
    :param bool grid: Whether to show a grid.
    :param str name: Name to show as window title.
    :param logger log: Parent logger to handle log entries. Creates the child 'PlotMulti'.
    """

    def __init__(
        self,
        parent: DataLoggerGuiProtocol,
        autoCut: int = 0,
        grid: bool = False,
        log: Optional[logging.Logger] = None,
        **kwargs,
    ) -> None:
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["pen", "key"])
        self.model.dataChanged.connect(self.lineConfigurationChanged)
        self.lines: dict[str, pg.PlotDataItem] = {}  # The lines themselves. key: line
        self.pens: dict[str, str] = {}  # Pen names for restoring them. key: pen name
        self.legend_entries: dict[str, pg.PlotDataItem] = {}  # key: line for legend
        self.references: dict[str, int] = {}  # key: axis index

        super().__init__(parent=parent, autoCut=autoCut, grid=grid, log=log, **kwargs)

        self.tvLines.setModel(self.model)
        self._adjustView()
        sm: QtCore.QItemSelectionModel = self.tvLines.selectionModel()  # type: ignore
        sm.currentChanged.connect(self.showValues)

        self.log.info("MultiPlot created.")

    def _setup_actions(self):
        super()._setup_actions()
        self.action_show_lines = QtGui.QAction("Lines setup...")  # type: ignore
        self.action_show_lines.setIconText("ls")
        self.action_show_lines.setToolTip("Show the lines setup.")
        self.action_show_lines.setCheckable(True)
        self.action_show_lines.setChecked(True)
        self.action_show_lines.toggled.connect(self.show_line_settings)

    def _setup_ui(self):
        super()._setup_ui()
        for action in (
            self.actionlg,
            self.actionly,
            self.actionv,
            self.action_show_lines,
            self.actionvls,
            self.actionEvaluate,
            self.action_show_toolbar,
        ):
            self.toolbar.addAction(action)
            self.menu.addAction(action)
        self.tvLines = QtWidgets.QTableView()
        self.tvLines.setToolTip(
            "<html><head/><body><p>Select the color of the key to show. Either "
            "as a name or as RGB.</p><p>Prefix &quot;n,&quot; to show it to "
            'the n<span style=" vertical-align:super;">th</span> right axis.'
            "</p><p>Only the main axis and the first right axis get plot "
            "transforms and &quot;view all&quot; via the &quot;A&quot; button."
            "</p></body></html>"
        )
        self.tvLines.setSelectionMode(QtWidgets.QTableView.SelectionMode.SingleSelection)
        self.tvLines.verticalHeader().setVisible(False)  # type: ignore
        self.pbAutoRange = QtWidgets.QToolButton()
        self.pbAutoRange.setText("A")
        self.pbAutoRange.setToolTip("Set all axes to auto Y range (Ctrl + A).")
        self.pbAutoRange.setShortcut("Ctrl+A")
        # self.bbX: minimum size 90x0
        self.pbLines = QtWidgets.QToolButton()
        self.pbLines.setText("ls")
        self.pbLines.setToolTip("Show the lines setup.")
        self.pbLines.setCheckable(True)
        self.pbLines.setChecked(True)
        self.pbLines.clicked.connect(self.action_show_lines.setChecked)

        # Connect actions to slots
        self.pbAutoRange.clicked.connect(self.setAutoRange)

    def _layout(self):
        display_box = QtWidgets.QHBoxLayout()
        display_box.setSpacing(1)
        display_box.setContentsMargins(0, 0, 0, 0)
        for widget in (self.tvLines, self.plotWidget):
            display_box.addWidget(widget)
        display_box.setStretchFactor(self.plotWidget, 10)

        button_box = QtWidgets.QHBoxLayout()
        button_box.setSpacing(1)
        button_box.setContentsMargins(0, 0, 0, 0)
        for widget in (
            self.pbOptions,
            self.pbAutoRange,
            self.pbLines,
            self.bbX,
            self.sbAutoCut,
            self.lbValue,
            self.lbEvaluation,
        ):
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
        self.plotWidget.addLegend(
            brush=(255, 255, 255, 64), labelTextColor=0.9, horSpacing=20, verSpacing=-10
        )
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
            key = self.model.item(i, 1).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
            pen_color = self.model.item(i, 0).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
            lines[key] = pen_color
        return lines

    def set_lines(self, lines: dict[str, str]) -> None:
        """Set the lines definitions."""
        for i in range(self.model.rowCount()):
            key = self.model.item(i, 1).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
            pen_color = lines.get(key, "")
            self.model.item(i, 0).setData(pen_color, Qt.ItemDataRole.DisplayRole)  # type: ignore

    def get_configuration(self) -> dict[str, Any]:
        """Get the current plot configuration."""
        configuration = super().get_configuration()
        configuration.update(
            {
                "lines": self.get_lines(),
                "y_key": self.keys[1],
            }
        )
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
            self.pbLines.setChecked(True)

    @pyqtSlot()
    def update(self):
        """Update the plots."""
        x_key, y_key = self.keys
        try:
            if x_key == "index":
                x_key = None
            for key, line in self.lines.items():
                data_pairs = self.main_window.get_xy_data(
                    y_key=key, x_key=x_key, start=-self.autoCut
                )
                line.setData(*data_pairs)
        except KeyError:
            return  # no data
        try:
            value = self.main_window.get_data(y_key, start=-1)[0]
            units = self.main_window.current_units.get(y_key, "")
            self.lbValue.setText(f"{y_key}: {value:.8g} {units}")
        except (IndexError, KeyError, TypeError):
            pass  # no data
        except ValueError:
            self.lbValue.setText(f"{y_key}: {self.main_window.get_data(y_key, start=-1)[0]}")
        except Exception as exc:
            self.log.exception(f"Updating data failed with '{exc}'", exc_info=exc)
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
        keys = self.main_window.get_data_keys()
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
        key = self.model.itemFromIndex(topLeft.siblingAtColumn(1)).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
        pen_color = self.model.itemFromIndex(topLeft).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
        if pen_color:
            parts = pen_color.split(",")
            try:
                pen = pg.mkPen(parts.pop())
            except ValueError:
                self.model.itemFromIndex(topLeft).setData("", Qt.ItemDataRole.DisplayRole)  # type: ignore
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
            self.legend_entries[key] = self.plotWidget.plot([], [], name=f"{axis}: {key}", pen=pen)
        else:
            self.lines[key] = self.plotWidget.plot([], [], name=key, pen=pen)

    def _removeLine(self, key: str) -> None:
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

    def showValues(
        self, current: QtCore.QModelIndex, previous: Optional[QtCore.QModelIndex] = None
    ) -> None:
        """Show the values of the selected key."""
        if self.pbLines.isChecked():
            self.keys[1] = self.model.item(current.row(), 1).data(Qt.ItemDataRole.DisplayRole)  # type: ignore
            self._last_index = current

    def _adjustView(self) -> None:
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
