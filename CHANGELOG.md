# CHANGELOG

## [unreleased]

### Changed

- **Breaking:** rename `MotorController` to `TMCMotorActor` and `MotorDirector` to `TMCMotorDirector`

### Added

- `BaseMainWindow` has `show_status_bar_message` method.
- DataLoggerGUI and its variants have now methods to access the data, which allows adding extra data.

### Fixed

- Fix DataLogger multiplot window to show value.
- Fix DataLogger start to unpause correctly [#13](https://github.com/BenediktBurger/pyleco-extras/issues/13)


## [0.1.0] 2024-02-02

_Initial release_

[unreleased]: https://github.com/BenediktBurger/pyleco-extras/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BenediktBurger/pyleco-extras/releases/tag/v0.1.0
