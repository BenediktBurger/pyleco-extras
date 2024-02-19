# Standard packages.
import datetime
import logging
from typing import Any, Optional

# 3rd party
from qtpy.QtCore import Signal  # type: ignore

from pyleco.core import COORDINATOR_PORT, PROXY_SENDING_PORT
from pyleco.management.data_logger import DataLogger, TriggerTypes, ValuingModes
from pyleco.utils.pipe_handler import PipeHandler
from pyleco.utils.events import Event
from pyleco.utils.listener import Listener
from pyleco.utils.qt_listener import ListenerSignals


class Signals(ListenerSignals):
    """Signals for the DataLogger message handler."""

    started = Signal()
    configuration_changed = Signal(dict)
    datapoint_ready = Signal(dict)
    plot_configuration_changed = Signal(list)


class DataLoggerCore(PipeHandler, DataLogger):
    """Modified pyleco DataLogger class to serve as a Core, with Qt elements."""

    def __init__(self, name: str, signals: Signals, directory: str = ".", **kwargs) -> None:
        super().__init__(name=name, directory=directory, **kwargs)
        self.signals = signals
        self.register_on_name_change_method(self.signals.name_changed.emit)
        self._previous_trigger: Optional[TriggerTypes] = None

    def calculate_data(self) -> dict[str, Any]:
        # might enter the datalogger itself.
        d = super().calculate_data()
        if "time_h" in d:
            if "time" in d:
                v = d["time"] / 3600
            else:
                now = datetime.datetime.now(datetime.timezone.utc)
                time = (now - self._today_zero).total_seconds()
                v = time / 3600
            d["time_h"] = v
            self.lists["time_h"][-1] = v
        return d

    def make_datapoint(self) -> dict[str, Any]:
        datapoint = super().make_datapoint()
        self.signals.datapoint_ready.emit(datapoint)
        return datapoint

    def set_configuration(self, configuration: dict[str, Any]) -> None:
        self.signals.configuration_changed.emit(configuration)

    def set_plot_configuration(self, plot_configuration: list[dict[str, Any]]) -> None:
        self.signals.plot_configuration_changed.emit(plot_configuration)

    def start_collecting(
        self,
        *,
        variables: Optional[list[str]] = None,
        units: Optional[dict[str, Any]] = None,
        trigger_type: Optional[TriggerTypes] = None,
        trigger_timeout: Optional[float] = None,
        trigger_variable: Optional[str] = None,
        valuing_mode: Optional[ValuingModes] = None,
        value_repeating: Optional[bool] = None,
    ) -> None:
        retv = super().start_collecting(
            variables=variables,
            units=units,
            trigger_type=trigger_type,
            trigger_timeout=trigger_timeout,
            trigger_variable=trigger_variable,
            valuing_mode=valuing_mode,
            value_repeating=value_repeating,
        )
        conf = dict(
            variables=variables,
            units=units,
            trigger_timeout=trigger_timeout,
            trigger_type=trigger_type,
            trigger_variable=trigger_variable,
            valuing_mode=valuing_mode,
            value_repeating=value_repeating,
        )
        for key in list(conf.keys()):
            if conf[key] is None:
                del conf[key]
        self.set_configuration(conf)
        self.signals.started.emit()
        self._today_zero = datetime.datetime.combine(
            self.today, datetime.time(), datetime.timezone.utc
        )
        return retv

    def register_rpc_methods(self) -> None:
        super().register_rpc_methods()
        self.register_rpc_method(self.set_plot_configuration)
        self.register_rpc_method(self.pause)
        self.register_rpc_method(self.set_trigger_type)
        self.register_rpc_method(self.set_trigger_interval)
        self.register_rpc_method(self.set_trigger_variable)
        self.register_rpc_method(self.set_configuration)

    # additional features, might enter the DataLogger itself
    def pause(self, pause_enabled: bool) -> None:
        """Pause or resume the measurement."""
        if pause_enabled:
            if self._previous_trigger is None:
                # Store old values.
                self._previous_trigger = self.trigger_type
                # Pause measurement
                self.trigger_type = TriggerTypes.NONE
                try:
                    self.timer.cancel()
                except AttributeError:
                    pass
        else:
            if self._previous_trigger is not None:
                self.trigger_type = self._previous_trigger
                if self.trigger_type == TriggerTypes.TIMER:
                    self.start_timer_trigger()
                self._previous_trigger = None

    def set_trigger_type(self, trigger_type: TriggerTypes) -> None:
        try:
            self.timer.cancel()
        except AttributeError:
            pass
        self.trigger_type = trigger_type
        if trigger_type == TriggerTypes.TIMER:
            self.start_timer_trigger()

    def set_trigger_interval(self, interval: float) -> None:
        try:
            self.timer.interval = interval
        except AttributeError:
            pass

    def set_trigger_variable(self, variable: str) -> None:
        self.trigger_variable = variable


class DataLoggerListener(Listener):
    """Listener which contains a DataLogger as a MessageHandler."""

    message_handler: DataLoggerCore

    def __init__(
        self,
        name: str,
        host: str = "localhost",
        port: int = COORDINATOR_PORT,
        data_host: Optional[str] = None,
        data_port: int = PROXY_SENDING_PORT,
        logger: Optional[logging.Logger] = None,
        timeout: float = 1,
        **kwargs,
    ) -> None:
        super().__init__(
            name=name,
            host=host,
            port=port,
            data_host=data_host,
            data_port=data_port,
            logger=logger,
            timeout=timeout,
            **kwargs,
        )
        self.signals = Signals()

    def _listen(
        self,
        name: str,
        stop_event: Event,
        coordinator_host: str,
        coordinator_port: int,
        data_host: str,
        data_port: int,
    ) -> None:
        self.message_handler = DataLoggerCore(
            name,
            signals=self.signals,
            host=coordinator_host,
            port=coordinator_port,
            data_host=data_host,
            data_port=data_port,
        )
        self.message_handler.listen(stop_event=stop_event)
