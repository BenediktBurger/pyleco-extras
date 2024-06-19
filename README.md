# pyleco-extras

[![codecov](https://codecov.io/gh/BenediktBurger/pyleco-extras/graph/badge.svg?token=BHDA9OKK7C)](https://codecov.io/gh/BenediktBurger/pyleco-extras)
[![Common Changelog](https://common-changelog.org/badge.svg)](https://common-changelog.org)

Additional content for [PyLECO](https://github.com/pymeasure/pyleco) the python reference implementation of the Laboratory Experiment COntrol (LECO) protocol (https://github.com/pymeasure/leco-protocol).

This module offers additional actors, directors, etc.
It also offers some GUI utils for easier control of the PyLECO Components.


## Installation

1. Clone this repository,
2. change your working directory to this file,
3. Install with pip editable: `pip install -e .`

For updates just pull the main branch.


## GUI Tools

Some GUIs related to PyLECO.
They are in the [gui](pyleco_extras/gui/) folder.


### BaseMainWindow

In the [gui_utils](pyleco_extras/gui_utils/), the `BaseMainWindow` and `BaseSettings` classes offer default classes for a GUI main window and a corresponding settings dialog window.
The BaseMainWindow has a `Listener` and a `DataPublisher` (from PyLECO) already up and running.
The BaseSettings allows easy customization of a settings dialog class.

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


## Actors / Directors

Actors and Directors.
They are, analogous to PyLECO in corresponding [actors](pyleco_extras/actors/) and [directors](pyleco_extras/directors/) folders.

### Analyzing director

This director can analyze an instrument (especially `pymeasure.Instrument`) and create a device, which seems to be such an instrument.
It reproduces all methods, properties, and channels (with methods, properties, and subchannels recursively).
That removes the need to create a director for a specific instrument, but offers all the tools as if the instrument were local.

### Trinamic Motor Cards

The `actors.tmc_motor_actor` offers an Actor for Trinamic motor cards.
The `directors.tmc_motor_director` offers the corresponding Director, which can be used as an in-place replacement for trinamic motor cards objects of the [pytrinamic](https://github.com/trinamic/PyTrinamic) project.


## Tools

Other tools in the [tools](pyleco_extras/tools/) folder.

### Topic Collector

The TopicTollector listens to published data (data protocol) for some time and collects all the topics in order to show, what is available.


## Utils

More utils in [utils](pyleco_extras/utils/) folder, analogous to PyLECO.

### Extended Publisher

The extended Publisher is one, which can send `pint.Quantity` and numpy objects.
The default JSON encoder does not handle these objects.


### Republisher

The Republisher listens to messages of the data protocol and publishes new values based on these.
For example, it can use a calibration to convert a measurement data to a calibrated value.
