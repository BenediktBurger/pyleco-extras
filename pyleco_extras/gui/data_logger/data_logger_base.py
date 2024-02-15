"""
Base File for the DataLogger family.
"""


# Standard packages.
import logging
from pathlib import Path
import time
from typing import Any, Iterable, Optional

# 3rd party
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import pyqtSlot
from pyqtgraph.dockarea import DockArea, Dock

from pyleco.management.data_logger import TriggerTypes, ValuingModes

from pyleco_extras.gui_utils.base_main_window import LECOBaseMainWindowDesigner, start_app
from pyleco_extras.gui.data_logger.data.single_plot_widget import SinglePlotWidget, PlotGroupWidget
from pyleco_extras.gui.data_logger.data.multi_plot_widget import MultiPlotWidget

log = logging.getLogger(__name__)
log.addHandler(logging.StreamHandler())


class DataLoggerBase(LECOBaseMainWindowDesigner):
    """Base class for the DataLogger family.
    """
    data_length_limit: int = 0  # length of list lengths

    actionStart: QtGui.QAction
    actionPause: QtGui.QAction
    actionSave: QtGui.QAction
    actionAutoSave: QtGui.QAction
    actionCopyLastDatapoint: QtGui.QAction
    actionLimitDataLength: QtGui.QAction
    actionSinglePlot: QtGui.QAction
    actionMultiPlot: QtGui.QAction
    actionClearPlots: QtGui.QAction
    actionConfig: QtGui.QAction

    leSavedName: QtWidgets.QLineEdit
    cbTrigger: QtWidgets.QRadioButton
    cbTimer: QtWidgets.QRadioButton
    leTrigger: QtWidgets.QLineEdit
    sbTimeout: QtWidgets.QSpinBox
    cbValueLast: QtWidgets.QRadioButton
    cbValueMean: QtWidgets.QRadioButton
    cbRepeat: QtWidgets.QCheckBox
    leHeader: QtWidgets.QPlainTextEdit
    leVariables: QtWidgets.QLineEdit
    lbVariables: QtWidgets.QLabel
    lbValues: QtWidgets.QLabel

    tabWidget: QtWidgets.QTabWidget
    toolBar: QtWidgets.QToolBar

    def __init__(self, name: str, **kwargs) -> None:
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, ui_file_name="DataLogger",
                         ui_file_path=Path(__file__).parent / "data",
                         **kwargs)

        # Load the user interface file, and configure the dock area and show it.
        self.dockArea = DockArea()
        self.dock_count: int = 0
        self.tabWidget.addTab(self.dockArea, "&Plots")
        self.lbCount = QtWidgets.QLabel()
        self.statusBar().addWidget(self.lbCount)  # type: ignore
        self.lbCount.show()

        self.signals = self.Signals()

        self.setup_actions()
        self.setup_buttons()
        self.setup_lists()
        self.setup_timers()

        # Configure the Data Logger.
        self.setSettings()
        self.restore_configuration()
        self.restore_plot_configuration()

        log.info(f"{name} initialized.")

    class Signals(QtCore.QObject):
        """Signals for the DataLogger."""
        starter = QtCore.pyqtSignal()  # start the listener
        started = QtCore.pyqtSignal()  # a new measurement started, update variable names
        update_plots = QtCore.pyqtSignal()  # update the plots.
        closing = QtCore.pyqtSignal()

    def setup_actions(self) -> None:
        # Connect actions to slots.

        #   Plot actions
        self.actionSinglePlot.triggered.connect(self.spawnSinglePlot)
        self.actionMultiPlot.triggered.connect(self.spawnMultiPlot)
        self.actionClearPlots.triggered.connect(self.clear_plots)

        #   Configuration
        self.actionConfig.triggered.connect(self.save_configuration)

        #   Measurement actions
        # self.actionStart.triggered.connect(self.start)
        # self.actionSave.triggered.connect(self.saveDataClicked)
        # self.actionPause.toggled.connect(self.pause)
        # self.actionCopyLastDatapoint.triggered.connect(self.copy_last_data_point)
        # self.actionAutoSave

    def setup_buttons(self) -> None:
        """Connect buttons to slots."""
        pass

    def setup_lists(self):
        self.plots: list[PlotGroupWidget] = []
        self.lists: dict[str, list[Any]] = {}
        self.current_units: dict[str, str] = {}  # for the current measurement
        self._variables: Iterable[str]
        self._units: dict[str, str]

    def cut_lists(self):
        """Cut the lists to max length."""
        if self.data_length_limit == 0:
            return  # cutting is disabled
        log.debug(f"Lists cut to length {self.data_length_limit}.")
        for key, li in self.lists.items():
            self.lists[key] = li[-self.data_length_limit:]

    def setup_timers(self) -> None:
        # Timers
        #   As trigger
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.make_data_point)
        #   For lag detection
        self.lag_detection_timer = QtCore.QTimer()
        self.lag_detection_timer.setInterval(750)
        self.lag_detection_timer.timeout.connect(self.heartbeat)
        self._limit = time.perf_counter()
        self.lag_detection_timer.start()

    def read_configuration(self) -> dict[str, Any]:
        """Read the last configuration."""
        settings = QtCore.QSettings()
        return settings.value('configuration', type=dict)

    def restore_configuration(self) -> None:
        """Restore the last configuration"""
        self.set_configuration(self.read_configuration())
        for variable in self.variables:
            self.lists[variable] = []

    @pyqtSlot()
    def closeEvent(self, event) -> None:
        """On closure close everything."""
        log.info("Closing.")
        self.stop_listen()
        self.store_plot_configuration()
        self.signals.closing.emit()
        self.store_configuration()
        event.accept()

    def setSettings(self):
        settings = QtCore.QSettings()
        self.data_length_limit = settings.value("dataLengthLimit", 0, int)

    def get_plot_configuration(self) -> list[dict[str, Any]]:
        plot_configuration = []
        for dock in self.dockArea.docks.values():
            if dock._container is None:
                continue
            config = {"name": dock.name()}
            config.update(dock.widgets[0].get_configuration())
            plot_configuration.append(config)
        return plot_configuration

    def store_plot_configuration(self) -> None:
        """Store the configuration of the plots."""
        settings = QtCore.QSettings()
        dock_configuration = self.dockArea.saveState()
        settings.setValue("dock_configuration", dock_configuration)
        plot_configuration = self.get_plot_configuration()
        settings.setValue("plot_configuration", plot_configuration)

    def set_plot_configuration(self, plot_configuration: list[dict[str, Any]]) -> None:
        self.clear_plots()
        if plot_configuration is not None:
            for plot_config in plot_configuration:
                self.spawnPlot(**plot_config)
                name = plot_config.get("name")
                if name is not None and (number := int(name.split()[-1])) >= self.dock_count:
                    self.dock_count = number + 1

    def restore_plot_configuration(self) -> None:
        """Restore the plot configuration."""
        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(QtCore.QByteArray(geometry))
        try:
            plot_configuration = settings.value("plot_configuration")
        except TypeError as exc:
            log.exception("Loading plot configuration failed.", exc_info=exc)
        else:
            self.set_plot_configuration(plot_configuration=plot_configuration)
        dock_configuration = settings.value("dock_configuration")
        if dock_configuration is not None:
            try:
                self.dockArea.restoreState(dock_configuration)
            except Exception as exc:
                log.exception("Plot dock configuration could not be restored.", exc_info=exc)

    def store_configuration(self) -> None:
        """Store the currently used configuration."""
        settings = QtCore.QSettings()
        settings.setValue('configuration', self.get_configuration())
        # # Store the window geometry
        settings.setValue("geometry", self.saveGeometry())

    def get_logger_configuration(self) -> dict[str, Any]:
        config = {}
        # Trigger
        config['trigger_type'] = self.trigger_type.value
        config['trigger_timeout'] = self.trigger_timeout
        config['trigger_variable'] = self.trigger_variable
        # Value
        config['variables'] = self.variables
        config['units'] = self.units
        config['valuing_mode'] = self.valuing_mode
        config['value_repeating'] = self.value_repeating
        return config

    def get_gui_configuration(self) -> dict[str, Any]:
        config = {}
        config['header'] = self.leHeader.document().toPlainText()  # type: ignore
        config['unitsText'] = ""  # to clear it for feature removal
        config['autoSave'] = self.actionAutoSave.isChecked()
        config['pause'] = self.actionPause.isChecked()
        return config

    def get_configuration(self) -> dict[str, Any]:
        """Get the currently used configuration as a dictionary."""
        config = self.get_logger_configuration()
        config.update(self.get_gui_configuration())
        return config

    def _read_variables_and_units(self) -> None:
        var_text = self.leVariables.text().replace(": ", ":").replace(",", " ")
        raw_vars = var_text.split()
        variables = []
        units = {}
        for raw_var in raw_vars:
            if ":" in raw_var:
                v, u = raw_var.split(":", maxsplit=1)
                units[v] = u
            else:
                v = raw_var
            variables.append(v)
        self._variables = variables
        self._units = units

    def _update_variables_and_units(self) -> None:
        """Update the line with variables and units."""
        vars = []
        for var in self._variables:
            if unit := self._units.get(var):
                vars.append(":".join((var, unit)))
            else:
                vars.append(var)
        self.leVariables.setText(", ".join(vars))

    @property
    def variables(self) -> Iterable[str]:
        self._read_variables_and_units()
        return self._variables

    @variables.setter
    def variables(self, value: Iterable[str]) -> None:
        self._variables = value
        self._update_variables_and_units()

    @property
    def units(self) -> dict[str, str]:
        self._read_variables_and_units()
        return self._units

    @units.setter
    def units(self, value: dict[str, str]) -> None:
        self._units = value
        self._update_variables_and_units()

    @property
    def trigger_type(self) -> TriggerTypes:
        """Control what a new measurement point triggers."""
        if self.cbTimer.isChecked():
            return TriggerTypes.TIMER
        elif self.cbTrigger.isChecked():
            return TriggerTypes.VARIABLE
        else:
            return TriggerTypes.NONE

    @trigger_type.setter
    def trigger_type(self, value: TriggerTypes | str) -> None:
        match value:
            case TriggerTypes.NONE:
                self.actionPause.setChecked(True)
            case TriggerTypes.TIMER:
                self.cbTimer.setChecked(True)
            case TriggerTypes.VARIABLE:
                self.cbTrigger.setChecked(True)

    @property
    def trigger_timeout(self) -> float:
        """Control the timeout for timer trigger in s."""
        return self.sbTimeout.value() / 1000

    @trigger_timeout.setter
    def trigger_timeout(self, value: float) -> None:
        self.sbTimeout.setValue(int(value * 1000))

    @property
    def trigger_variable(self) -> str:
        return self.leTrigger.text()

    @trigger_variable.setter
    def trigger_variable(self, value: str) -> None:
        self.leTrigger.setText(value)

    @property
    def value_repeating(self) -> bool:
        return self.cbRepeat.isChecked()

    @value_repeating.setter
    def value_repeating(self, value: bool) -> None:
        self.cbRepeat.setChecked(value)

    @property
    def valuing_mode(self) -> ValuingModes:
        if self.cbValueLast.isChecked():
            return ValuingModes.LAST
        elif self.cbValueMean.isChecked():
            return ValuingModes.AVERAGE
        else:
            # default
            return ValuingModes.LAST

    @valuing_mode.setter
    def valuing_mode(self, value: ValuingModes | str) -> None:
        if value == ValuingModes.LAST:
            self.cbValueLast.setChecked(True)
        elif value == ValuingModes.AVERAGE:
            self.cbValueMean.setChecked(True)

    @pyqtSlot(dict)
    def set_configuration(self, configuration: dict[str, Any]) -> None:
        """Set measurement configuration according to the dict `configuration`."""
        self._set_config(**configuration)

    def read_legacy_units(self, text: str) -> dict[str, str]:
        """Interpreting the old units text and returning a corresponding dict."""
        units = {}
        for element in text.split(","):
            if element:
                try:
                    key, unit = element.split(":")
                except ValueError:
                    continue
                try:
                    units[key.strip()] = unit.strip()
                except Exception:
                    continue
        return units

    def _set_config(self,
                    trigger_type: str | None = None,
                    trigger_timeout: float | None = None,
                    trigger_variable: str | None = None,
                    valuing_mode: str | None = None,
                    value_repeating: bool | None = None,
                    header: str | None = None,
                    variables: Iterable[str] | None = None,
                    variablesText: str | None = None,
                    units: dict[str, str] | None = None,
                    unitsText: str | None = None,
                    meta: Any | None = None,
                    autoSaveInterval: float | None = None,
                    autoSave: bool | None = None,
                    autoCut: int | None = None,
                    pause: bool | None = None,
                    start: bool = False,
                    **kwargs
                    ) -> None:
        settings = QtCore.QSettings()
        # deprecated values
        if (trigger := kwargs.get("trigger")):
            self.trigger_type = trigger
        # end of deprecated values
        if trigger_type is not None:
            self.trigger_type = trigger_type
        if trigger_timeout is not None:
            self.trigger_timeout = trigger_timeout
        if trigger_variable is not None:
            self.trigger_variable = trigger_variable
        if valuing_mode is not None:
            self.valuing_mode = valuing_mode
        if value_repeating is not None:
            self.value_repeating = value_repeating
        if variables is not None:
            self.variables = variables
        if variablesText is not None:
            self.leVariables.setText(variablesText)
        if units is not None:
            self.units = units
        if header is not None:
            self.leHeader.setPlainText(header)
        if unitsText is not None:
            self.units.update(self.read_legacy_units(unitsText))
        if meta is not None:
            self.user_data = meta
        if autoSaveInterval is not None:
            self.auto_save_timer.setInterval(autoSaveInterval * 60 * 1000)  # min to ms  # type: ignore  # noqa
            settings.setValue('autoSaveInterval', autoSaveInterval)
        if autoSave is not None:
            self.actionAutoSave.setChecked(autoSave)
        if autoCut is not None:
            settings.setValue('autoCut', autoCut)
        if pause is not None:
            self.actionPause.setChecked(pause)
        log.debug(f"Additional arguments {kwargs}")
        # Start the logging.
        if start:
            self.start()

    def start_collecting(self, *,
                         variables: Optional[list[str]] = None,
                         units: Optional[dict[str, Any]] = None,
                         trigger_type: Optional[TriggerTypes] = None,
                         trigger_timeout: Optional[float] = None,
                         trigger_variable: Optional[str] = None,
                         valuing_mode: Optional[ValuingModes] = None,
                         value_repeating: Optional[bool] = None,
                         ) -> None:
        """Start collecting data."""
        self._set_config(variables=variables,
                         units=units,
                         trigger_type=trigger_type,
                         trigger_timeout=trigger_timeout,
                         trigger_variable=trigger_variable,
                         value_repeating=value_repeating,
                         valuing_mode=valuing_mode,
                         )
        self.start()

    def heartbeat(self) -> None:
        """Measure the time since the last execution for lag detection."""
        now = time.perf_counter()
        if now > self._limit + 5:  # limit for pausing measurement altogether
            self.actionPause.setChecked(True)
        self._limit = now + 1  # limit for plot update

    # GUI application interactions
    @pyqtSlot()
    def spawnMultiPlot(self) -> None:
        """Spawn a new plot."""
        self.spawnPlot(type="MultiPlotWidget")

    @pyqtSlot()
    def spawnSinglePlot(self) -> None:
        """Spawn a new plot with autocut."""
        self.spawnPlot()

    def spawnPlot(self, autoCut: Optional[int] = None, type: str = "",
                  name: Optional[str] = None,
                  **kwargs) -> None:
        """Spawn a new plot window.

        :param autoCut: Last values to show. If None, read from settings. 0 means all.
        :param multi: Show the multi plot window.
        """
        settings = QtCore.QSettings()
        grid = settings.value('grid', True, type=bool)
        if autoCut is None:
            autoCut = settings.value('autoCut', 200, type=int)
        if name is None:
            name = f"Plot {self.dock_count}"
            self.dock_count += 1
        if type == "MultiPlotWidget":
            plot = MultiPlotWidget(self,
                                   autoCut=autoCut,  # type: ignore
                                   grid=grid,
                                   log=log,
                                   **kwargs)
            dock = Dock(name=name, closable=True, widget=plot)
        else:
            plot = SinglePlotWidget(self,
                                    autoCut=autoCut,  # type: ignore
                                    grid=grid,
                                    log=log,
                                    **kwargs)
            dock = Dock(name=name, closable=True, widget=plot)
        self.dockArea.addDock(dock)

        self.signals.closing.connect(dock.close)
        self.signals.closing.connect(plot.close)  # type: ignore
        self.signals.started.connect(plot.updateKeys)
        self.signals.update_plots.connect(plot.update)
        self.tabWidget.setCurrentIndex(1)

    @pyqtSlot()
    def clear_plots(self) -> None:
        """Remove all plots."""
        for dock in self.dockArea.docks.values():
            dock.close()
        self.dock_count = 0

    "Default settings"
    @pyqtSlot()
    def save_configuration(self) -> None:
        """Save an executable configuration file according to the current configuration."""
        # TODO adjust according to recent development
        settings = QtCore.QSettings()
        config = self.get_logger_configuration()
        p_conf = self.get_plot_configuration()
        text = "\n".join([
            "from pyleco.directors.data_logger_director import DataLoggerDirector",
            "", "",  # empty lines
            f"name = '{self.windowTitle()}'",
            "", "",  # empty lines
            "configuration = {",
            *[f"""    '{key}': {f'"{value}"' if isinstance(value, str) else value},"""
              for key, value in config.items()],
            "}",
            "", "",  # empty lines
            f"gui_configuration = {repr(self.get_gui_configuration())}",
            "", "",  # empty lines
            "plot_configuration = [",
            *[f"    {repr(conf)}," for conf in p_conf],
            "]",
            "", "",  # empty lines
            "if __name__ == '__main__':",
            "    with DataLoggerDirector(name='call' + name, actor=name) as d:",
            "        # print(d.save_data())",
            "        print(d.ask_rpc(method='set_configuration', configuration=gui_configuration))",
            "        print(d.start_collecting(**configuration))",
            "        print(d.ask_rpc(method='set_plot_configuration', plot_configuration=plot_configuration))",  # noqa
            "",  # empty line
        ])
        start = settings.value("configPath")
        path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Configuration save path",
            f"{start}/LogConfiguration",
            "Python files (*.py *.pyw)",
        )[0]
        if path:
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
            settings.setValue("configPath", path.rsplit("/", maxsplit=1)[0])
        return  # do nothing

    # GUI measurement interactions
    @pyqtSlot()
    def start(self) -> None:
        raise NotImplementedError

    @pyqtSlot()
    def make_data_point(self) -> None:
        """Store a datapoint."""
        raise NotImplementedError

    @pyqtSlot(dict)
    def show_data_point(self, datapoint: dict[str, Any]) -> None:
        self.show_list_length()
        self.lbVariables.setText("\n".join(datapoint.keys()))
        self.lbValues.setText("\n".join(
            f"{value} {self.current_units.get(variable, '')}" for variable, value in datapoint.items()))  # noqa
        if time.perf_counter() < self._limit:
            # Only update plots, if no lag occurs.
            self.signals.update_plots.emit()

    def show_list_length(self):
        try:
            length = len(self.lists[list(self.lists.keys())[0]])
        except IndexError:
            length = 0
        else:
            self.lbCount.setText(f"Data points: {length}")
            if self.actionLimitDataLength.isChecked() and length > self.data_length_limit * 1.1:
                self.cut_lists()

    @pyqtSlot()
    def copy_last_data_point(self) -> None:
        """Copy the last datapoint to the clipboard."""
        text_elements = []
        for key, li in self.lists.items():
            text_elements.append(f"{key}:\t {li[-1]} {self.current_units.get(key, '')}")
        clipboard = QtWidgets.QApplication.instance().clipboard()  # type: ignore
        clipboard.setText("\n".join(text_elements))


if __name__ == "__main__":  # pragma: no cover
    start_app(main_window_class=DataLoggerBase)
