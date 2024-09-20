# v2.1 Release Notes

## [v2.1.0 (2024-09-19)](https://github.com/nautobot/nautobot-app-netbox-importer/releases/tag/v2.1.0)

### Added

- [#165](https://github.com/nautobot/nautobot-app-netbox-importer/issues/165) - Added `--trace-issues` argument to `nautobot-server import_netbox` command to log exception trace-backs.
- [#165](https://github.com/nautobot/nautobot-app-netbox-importer/issues/165) - Added `created` and `updated` to Nautobot model stats.
- [#166](https://github.com/nautobot/nautobot-app-netbox-importer/issues/166) - Added Nautobot `v2.2.x` support.
- [#168](https://github.com/nautobot/nautobot-app-netbox-importer/issues/168) - Added importing ConfigContext model.
- [#179](https://github.com/nautobot/nautobot-app-netbox-importer/issues/179) - Added Python 3.12 support.

### Changed

- [#166](https://github.com/nautobot/nautobot-app-netbox-importer/issues/166) - Changed importing locations to allow importing to many-to-many field `locations` if defined.

### Fixed

- [#165](https://github.com/nautobot/nautobot-app-netbox-importer/issues/165) - Fixed reporting non-imported (`save()` failed) instances to DiffSync library.
- [#174](https://github.com/nautobot/nautobot-app-netbox-importer/issues/174) - Fixed multi-select custom fields failing to import.

### Dependencies

- [#182](https://github.com/nautobot/nautobot-app-netbox-importer/issues/182) - Removed unused dependency tqdm.

### Documentation

- [#157](https://github.com/nautobot/nautobot-app-netbox-importer/issues/157) - Removed old screenshots.
- [#157](https://github.com/nautobot/nautobot-app-netbox-importer/issues/157) - Fixed NetBox and Nautobot version in package description.

### Housekeeping

- [#148](https://github.com/nautobot/nautobot-app-netbox-importer/issues/148) - Rebaked from the cookie `nautobot-app-v2.2.0`.
- [#151](https://github.com/nautobot/nautobot-app-netbox-importer/issues/151) - Rebaked from the cookie `nautobot-app-v2.2.1`.
- [#157](https://github.com/nautobot/nautobot-app-netbox-importer/issues/157) - Split test fixtures per minor Nautobot version.
- [#177](https://github.com/nautobot/nautobot-app-netbox-importer/issues/177) - Rebaked from the cookie `nautobot-app-v2.3.0`.
- [#179](https://github.com/nautobot/nautobot-app-netbox-importer/issues/179) - Rebaked from the cookie `nautobot-app-v2.3.2`.
- [#182](https://github.com/nautobot/nautobot-app-netbox-importer/issues/182) - Added Sample Data section to bug report issue template.
