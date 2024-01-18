# pyleco-extras

Additional content for [PyLECO](https://github.com/pymeasure/pyleco) the python reference implementation of the Laboratory Experiment COntrol (LECO) protocol (https://github.com/pymeasure/leco-protocol).

This module offers additional actors, directors, etc.
It also offers some GUI utils for easier control of the PyLECO Components.

## GUI Tools

They are in the [gui](pyleco_extras/gui/) folder.

### DataLogger

A graphical interface using under the hood the `pyleco.management.data_logger.DataLogger`.
It can show the accumulated data in real time and can configure the internal data logger.

The `DataLoggerRemote` is the same graphical interface which controls a DataLogger remotely, be it with or without GUI itself.

The `DataLoggerViewer` can show files saved by the DataLogger.

### LECOViewer

This tool shows all the Coordinators and the Components connected to a Coordinator.

### StarterGUI

It shows the tasks of one or several starters.
You can start/stop/restart tasks of these starters.

### LogLogger

The `LogLogger` logs the log entries published by other Components and shows the logs graphically.
