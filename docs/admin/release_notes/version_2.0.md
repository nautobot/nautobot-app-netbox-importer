# v2.0 Release Notes

## v2.0.0 (2024-03-04)

### Added

- [#130](https://github.com/nautobot/nautobot-app-netbox-importer/issues/130) - Added support for NetBox v3.0 - v3.7 and Nautobot v2.0 - v2.1.

### Changed

- [#126](https://github.com/nautobot/nautobot-app-netbox-importer/issues/126) - Replaced pydocstyle with ruff.

### Fixed

- [#146](https://github.com/nautobot/nautobot-app-netbox-importer/issues/146) - Fixed `units` field importer.
- [#146](https://github.com/nautobot/nautobot-app-netbox-importer/issues/146) - Fixed importer for `u_height` field to use default importer.
- [#146](https://github.com/nautobot/nautobot-app-netbox-importer/issues/146) - Fixed failing import when `CustomField.label` field is empty.
- [#146](https://github.com/nautobot/nautobot-app-netbox-importer/issues/146) - Fixed to use `add_issue()` instead of `logger.warning()`.
- [#146](https://github.com/nautobot/nautobot-app-netbox-importer/issues/146) - Fixed tests to use stats.

### Removed

- Support for NetBox 2.x and Nautobot 1.x.
